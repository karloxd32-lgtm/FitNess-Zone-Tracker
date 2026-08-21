import os,secrets,smtplib
from datetime import datetime,timedelta,timezone,date
from email.message import EmailMessage
from typing import Optional
import jwt
from fastapi import FastAPI,HTTPException,Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,EmailStr,Field
from passlib.context import CryptContext
from supabase import create_client

APP="Fitness Zone Tracker"
OWNER=os.getenv("OWNER_EMAIL","fitness.zone.tracker@gmail.com").lower()
SECRET=os.getenv("JWT_SECRET","CHANGE_ME")
pwd=CryptContext(schemes=["bcrypt"],deprecated="auto")
url=os.getenv("SUPABASE_URL"); key=os.getenv("SUPABASE_SERVICE_ROLE_KEY")
db=create_client(url,key) if url and key else None
app=FastAPI(title=APP)
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])

class Signup(BaseModel):
 name:str=Field(min_length=2,max_length=80); email:EmailStr; password:str=Field(min_length=8,max_length=128); confirm_password:str
class Login(BaseModel): email:EmailStr; password:str
class OTP(BaseModel): email:EmailStr; code:str=Field(min_length=6,max_length=6)
class Forgot(BaseModel): email:EmailStr
class Reset(BaseModel): email:EmailStr; code:str; new_password:str=Field(min_length=8); confirm_password:str
class Habit(BaseModel): name:str=Field(min_length=1,max_length=100)
class HabitLog(BaseModel): completed:bool
class Workout(BaseModel): title:str; workout_date:Optional[str]=None; duration_min:int=0; notes:str=""
class Exercise(BaseModel): name:str; sets:int=0; reps:int=0; weight_kg:float=0
class Food(BaseModel): name:str; serving:str=""; calories:float=0; protein_g:float=0; carbs_g:float=0; fat_g:float=0
class Meal(BaseModel):
 food_id:Optional[str]=None; meal_date:Optional[str]=None; meal_type:str="Other"; quantity:float=1
 calories:float=0; protein_g:float=0; carbs_g:float=0; fat_g:float=0
class Progress(BaseModel):
 log_date:Optional[str]=None; weight_kg:Optional[float]=None; steps:Optional[int]=None; water_ml:Optional[int]=None; sleep_hours:Optional[float]=None; notes:str=""
class Settings(BaseModel):
 calorie_target:float=2000; protein_target:float=120; carb_target:float=200; fat_target:float=60; water_target_ml:int=3000; step_target:int=8000; sleep_target:float=8
class Role(BaseModel): role:str
class Status(BaseModel): status:str
class Announcement(BaseModel): title:str; body:str

def needdb():
 if not db: raise HTTPException(500,"Supabase is not configured")
def now(): return datetime.now(timezone.utc)
def today(): return date.today().isoformat()
def user_email(email):
 needdb(); r=db.table("profiles").select("*").eq("email",email.lower()).maybe_single().execute(); return r.data
def user_id(uid):
 needdb(); r=db.table("profiles").select("*").eq("id",uid).maybe_single().execute(); return r.data
def role(u): return "owner" if u["email"].lower()==OWNER else u["role"]
def token(u):
 return jwt.encode({"sub":u["id"],"email":u["email"],"role":role(u),"exp":now()+timedelta(days=7)},SECRET,algorithm="HS256")
def auth(h):
 if not h or not h.lower().startswith("bearer "): raise HTTPException(401,"Login required")
 try: p=jwt.decode(h.split(" ",1)[1],SECRET,algorithms=["HS256"])
 except: raise HTTPException(401,"Session expired")
 u=user_id(p["sub"])
 if not u: raise HTTPException(401,"User not found")
 if u["status"]=="banned": raise HTTPException(403,"Account is suspended")
 return u
def owner(h):
 u=auth(h)
 if role(u)!="owner": raise HTTPException(403,"Owner only")
 return u
def staff(h):
 u=auth(h)
 if role(u) not in ("admin","owner"): raise HTTPException(403,"Admin only")
 return u
def touch(u): db.table("profiles").update({"last_activity":now().isoformat()}).eq("id",u["id"]).execute()
def send_mail(to,subject,body):
 su=os.getenv("SMTP_USER"); pw=os.getenv("SMTP_APP_PASSWORD")
 if not su or not pw: raise HTTPException(500,"Email service is not configured")
 m=EmailMessage();m["From"]=su;m["To"]=to;m["Subject"]=subject;m.set_content(body)
 with smtplib.SMTP(os.getenv("SMTP_HOST","smtp.gmail.com"),int(os.getenv("SMTP_PORT","587"))) as s:
  s.starttls();s.login(su,pw);s.send_message(m)
def otp(email,purpose):
 code=f"{secrets.randbelow(1000000):06d}"
 db.table("otp_codes").insert({"email":email.lower(),"code":code,"purpose":purpose,"expires_at":(now()+timedelta(minutes=10)).isoformat()}).execute()
 return code
def valid_otp(email,purpose,code):
 r=db.table("otp_codes").select("*").eq("email",email.lower()).eq("purpose",purpose).eq("code",code).order("created_at",desc=True).limit(1).execute()
 if not r.data:return False
 return datetime.fromisoformat(r.data[0]["expires_at"].replace("Z","+00:00"))>=now()

@app.get("/api/health")
def health(): return {"ok":True,"app":APP}

@app.post("/api/auth/signup")
def signup(x:Signup):
 needdb()
 if x.password!=x.confirm_password: raise HTTPException(400,"Passwords do not match")
 e=x.email.lower()
 if user_email(e): raise HTTPException(409,"Account already exists")
 r=db.table("profiles").insert({"name":x.name.strip(),"email":e,"password_hash":pwd.hash(x.password),"role":"owner" if e==OWNER else "user","status":"active","verified":False}).execute()
 u=r.data[0]; db.table("user_settings").insert({"user_id":u["id"]}).execute()
 c=otp(e,"signup"); send_mail(e,"Fitness Zone Tracker - Verification",f"Your verification code is {c}. It expires in 10 minutes.")
 return {"ok":True}

@app.post("/api/auth/verify")
def verify(x:OTP):
 if not valid_otp(x.email,"signup",x.code): raise HTTPException(400,"Invalid or expired OTP")
 u=user_email(x.email)
 db.table("profiles").update({"verified":True,"last_activity":now().isoformat()}).eq("id",u["id"]).execute()
 return {"token":token(u),"role":role(u)}

@app.post("/api/auth/login")
def login(x:Login):
 u=user_email(x.email)
 if not u or not u["verified"] or u["status"]=="banned" or not pwd.verify(x.password,u["password_hash"]): raise HTTPException(401,"Invalid email or password")
 touch(u); return {"token":token(u),"role":role(u),"name":u["name"]}

@app.post("/api/auth/forgot")
def forgot(x:Forgot):
 u=user_email(x.email)
 if u:
  c=otp(x.email,"reset");send_mail(x.email,"Fitness Zone Tracker - Reset Code",f"Your reset code is {c}. It expires in 10 minutes.")
 return {"ok":True}

@app.post("/api/auth/reset")
def reset(x:Reset):
 if x.new_password!=x.confirm_password: raise HTTPException(400,"Passwords do not match")
 if not valid_otp(x.email,"reset",x.code): raise HTTPException(400,"Invalid or expired OTP")
 db.table("profiles").update({"password_hash":pwd.hash(x.new_password)}).eq("email",x.email.lower()).execute()
 return {"ok":True}

@app.post("/api/auth/change-password")
def change_password(x:Reset,h:Optional[str]=Header(None)):
 u=auth(h)
 if x.new_password!=x.confirm_password or not pwd.verify(x.code,u["password_hash"]): raise HTTPException(400,"Invalid current password or confirmation")
 db.table("profiles").update({"password_hash":pwd.hash(x.new_password)}).eq("id",u["id"]).execute()
 return {"ok":True}

@app.get("/api/me")
def me(h:Optional[str]=Header(None)):
 u=auth(h); return {k:u[k] for k in ("id","name","email","role","status","verified","last_activity")}

@app.get("/api/settings")
def get_settings(h:Optional[str]=Header(None)):
 u=auth(h); r=db.table("user_settings").select("*").eq("user_id",u["id"]).maybe_single().execute(); return r.data or {}
@app.put("/api/settings")
def put_settings(x:Settings,h:Optional[str]=Header(None)):
 u=auth(h); row=x.model_dump();row["user_id"]=u["id"];row["updated_at"]=now().isoformat();db.table("user_settings").upsert(row).execute();touch(u);return row

@app.get("/api/dashboard")
def dashboard(h:Optional[str]=Header(None)):
 u=auth(h); d=today()
 hs=db.table("habits").select("id").eq("user_id",u["id"]).eq("active",True).execute().data or []
 logs=db.table("habit_logs").select("completed").eq("user_id",u["id"]).eq("log_date",d).execute().data or []
 ws=db.table("workouts").select("id").eq("user_id",u["id"]).eq("workout_date",d).execute().data or []
 ms=db.table("meal_logs").select("calories,protein_g,carbs_g,fat_g").eq("user_id",u["id"]).eq("meal_date",d).execute().data or []
 pr=db.table("body_progress").select("*").eq("user_id",u["id"]).eq("log_date",d).order("created_at",desc=True).limit(1).execute().data
 return {"habit_total":len(hs),"habit_completed":sum(1 for x in logs if x["completed"]),"workouts":len(ws),
 "calories":sum(float(x["calories"] or 0) for x in ms),"protein":sum(float(x["protein_g"] or 0) for x in ms),
 "carbs":sum(float(x["carbs_g"] or 0) for x in ms),"fat":sum(float(x["fat_g"] or 0) for x in ms),
 "progress":pr[0] if pr else {},"role":role(u)}

@app.get("/api/habits")
def get_habits(h:Optional[str]=Header(None)):
 u=auth(h);return db.table("habits").select("*").eq("user_id",u["id"]).eq("active",True).order("created_at").execute().data
@app.post("/api/habits")
def add_habit(x:Habit,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("habits").insert({"user_id":u["id"],"name":x.name.strip()}).execute();touch(u);return r.data[0]
@app.delete("/api/habits/{hid}")
def del_habit(hid:str,h:Optional[str]=Header(None)):
 u=auth(h);db.table("habits").update({"active":False}).eq("id",hid).eq("user_id",u["id"]).execute();return {"ok":True}
@app.put("/api/habits/{hid}/today")
def log_habit(hid:str,x:HabitLog,h:Optional[str]=Header(None)):
 u=auth(h);db.table("habit_logs").upsert({"user_id":u["id"],"habit_id":hid,"log_date":today(),"completed":x.completed}).execute();touch(u);return {"ok":True}
@app.get("/api/habits/today")
def habit_today(h:Optional[str]=Header(None)):
 u=auth(h);hs=db.table("habits").select("*").eq("user_id",u["id"]).eq("active",True).execute().data or [];ls=db.table("habit_logs").select("*").eq("user_id",u["id"]).eq("log_date",today()).execute().data or [];m={x["habit_id"]:x["completed"] for x in ls};return [{"id":x["id"],"name":x["name"],"completed":bool(m.get(x["id"]))} for x in hs]

@app.get("/api/workouts")
def get_workouts(h:Optional[str]=Header(None)):
 u=auth(h);return db.table("workouts").select("*").eq("user_id",u["id"]).order("workout_date",desc=True).limit(200).execute().data
@app.post("/api/workouts")
def add_workout(x:Workout,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("workouts").insert({"user_id":u["id"],"title":x.title,"workout_date":x.workout_date or today(),"duration_min":x.duration_min,"notes":x.notes}).execute();touch(u);return r.data[0]
@app.delete("/api/workouts/{wid}")
def del_workout(wid:str,h:Optional[str]=Header(None)):
 u=auth(h);db.table("workouts").delete().eq("id",wid).eq("user_id",u["id"]).execute();return {"ok":True}
@app.get("/api/workouts/{wid}/exercises")
def get_exercises(wid:str,h:Optional[str]=Header(None)):
 u=auth(h);return db.table("exercises").select("*").eq("workout_id",wid).eq("user_id",u["id"]).execute().data
@app.post("/api/workouts/{wid}/exercises")
def add_exercise(wid:str,x:Exercise,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("exercises").insert({"user_id":u["id"],"workout_id":wid,**x.model_dump()}).execute();touch(u);return r.data[0]
@app.delete("/api/exercises/{eid}")
def del_exercise(eid:str,h:Optional[str]=Header(None)):
 u=auth(h);db.table("exercises").delete().eq("id",eid).eq("user_id",u["id"]).execute();return {"ok":True}

@app.get("/api/foods")
def foods(h:Optional[str]=Header(None)):
 u=auth(h);return db.table("food_items").select("*").eq("user_id",u["id"]).order("name").execute().data
@app.post("/api/foods")
def add_food(x:Food,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("food_items").insert({"user_id":u["id"],**x.model_dump()}).execute();touch(u);return r.data[0]
@app.delete("/api/foods/{fid}")
def del_food(fid:str,h:Optional[str]=Header(None)):
 u=auth(h);db.table("food_items").delete().eq("id",fid).eq("user_id",u["id"]).execute();return {"ok":True}
@app.get("/api/meals")
def meals(h:Optional[str]=Header(None),meal_date:Optional[str]=None):
 u=auth(h);return db.table("meal_logs").select("*").eq("user_id",u["id"]).eq("meal_date",meal_date or today()).order("created_at").execute().data
@app.post("/api/meals")
def add_meal(x:Meal,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("meal_logs").insert({"user_id":u["id"],"food_id":x.food_id,"meal_date":x.meal_date or today(),"meal_type":x.meal_type,"quantity":x.quantity,"calories":x.calories,"protein_g":x.protein_g,"carbs_g":x.carbs_g,"fat_g":x.fat_g}).execute();touch(u);return r.data[0]
@app.delete("/api/meals/{mid}")
def del_meal(mid:str,h:Optional[str]=Header(None)):
 u=auth(h);db.table("meal_logs").delete().eq("id",mid).eq("user_id",u["id"]).execute();return {"ok":True}

@app.get("/api/progress")
def get_progress(h:Optional[str]=Header(None)):
 u=auth(h);return db.table("body_progress").select("*").eq("user_id",u["id"]).order("log_date",desc=True).limit(365).execute().data
@app.post("/api/progress")
def add_progress(x:Progress,h:Optional[str]=Header(None)):
 u=auth(h);r=db.table("body_progress").insert({"user_id":u["id"],"log_date":x.log_date or today(),**x.model_dump(exclude={"log_date"})}).execute();touch(u);return r.data[0]

@app.get("/api/announcements")
def anns(h:Optional[str]=Header(None)):
 auth(h);return db.table("announcements").select("*").order("created_at",desc=True).limit(50).execute().data

@app.get("/api/staff/users")
def users(h:Optional[str]=Header(None),q:str=""):
 u=staff(h);query=db.table("profiles").select("id,name,email,role,status,verified,last_activity,created_at").order("created_at",desc=True)
 if q:query=query.ilike("email",f"%{q}%")
 return query.limit(500).execute().data
@app.put("/api/staff/users/{uid}/status")
def set_status(uid:str,x:Status,h:Optional[str]=Header(None)):
 a=staff(h);t=user_id(uid)
 if not t:raise HTTPException(404,"User not found")
 if t["email"].lower()==OWNER:raise HTTPException(400,"Owner cannot be changed")
 if role(a)=="admin" and t["role"] in ("admin","owner"):raise HTTPException(403,"Admin cannot manage staff")
 if x.status not in ("active","banned"):raise HTTPException(400,"Invalid status")
 db.table("profiles").update({"status":x.status}).eq("id",uid).execute();return {"ok":True}
@app.get("/api/owner/stats")
def owner_stats(h:Optional[str]=Header(None)):
 owner(h);rows=db.table("profiles").select("status,last_activity,role").execute().data or [];cut=now()-timedelta(days=7)
 active=0
 for x in rows:
  if x["status"]=="active" and x["last_activity"]:
   try:
    if datetime.fromisoformat(x["last_activity"].replace("Z","+00:00"))>=cut:active+=1
   except:pass
 return {"total":len(rows),"active":active,"offline":len(rows)-active,"admins":sum(x["role"]=="admin" for x in rows),"banned":sum(x["status"]=="banned" for x in rows)}
@app.put("/api/owner/users/{uid}/role")
def set_role(uid:str,x:Role,h:Optional[str]=Header(None)):
 owner(h);t=user_id(uid)
 if not t:raise HTTPException(404,"User not found")
 if t["email"].lower()==OWNER:raise HTTPException(400,"Owner cannot be changed")
 if x.role not in ("user","admin"):raise HTTPException(400,"Invalid role")
 db.table("profiles").update({"role":x.role}).eq("id",uid).execute();return {"ok":True}
@app.delete("/api/owner/users/{uid}")
def delete_user(uid:str,h:Optional[str]=Header(None)):
 owner(h);t=user_id(uid)
 if not t:raise HTTPException(404,"User not found")
 if t["email"].lower()==OWNER:raise HTTPException(400,"Owner cannot be deleted")
 db.table("profiles").delete().eq("id",uid).execute();return {"ok":True}
@app.post("/api/owner/announcements")
def add_announcement(x:Announcement,h:Optional[str]=Header(None)):
 u=owner(h);r=db.table("announcements").insert({"title":x.title,"body":x.body,"created_by":u["id"]}).execute();return r.data[0]
