create extension if not exists pgcrypto;

create table if not exists profiles (
 id uuid primary key default gen_random_uuid(),
 name text not null,
 email text unique not null,
 password_hash text not null,
 role text not null default 'user' check(role in ('user','admin','owner')),
 status text not null default 'active' check(status in ('active','banned')),
 verified boolean not null default false,
 last_activity timestamptz,
 created_at timestamptz not null default now()
);

create table if not exists otp_codes (
 id uuid primary key default gen_random_uuid(),
 email text not null,
 code text not null,
 purpose text not null check(purpose in ('signup','reset')),
 expires_at timestamptz not null,
 created_at timestamptz not null default now()
);

create table if not exists user_settings (
 user_id uuid primary key references profiles(id) on delete cascade,
 calorie_target numeric default 2000,
 protein_target numeric default 120,
 carb_target numeric default 200,
 fat_target numeric default 60,
 water_target_ml integer default 3000,
 step_target integer default 8000,
 sleep_target numeric default 8,
 updated_at timestamptz default now()
);

create table if not exists habits (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 name text not null,
 active boolean default true,
 created_at timestamptz default now()
);

create table if not exists habit_logs (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 habit_id uuid not null references habits(id) on delete cascade,
 log_date date not null,
 completed boolean default false,
 unique(user_id,habit_id,log_date)
);

create table if not exists workouts (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 workout_date date default current_date,
 title text not null,
 duration_min integer default 0,
 notes text,
 created_at timestamptz default now()
);

create table if not exists exercises (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 workout_id uuid not null references workouts(id) on delete cascade,
 name text not null,
 sets integer default 0,
 reps integer default 0,
 weight_kg numeric default 0,
 created_at timestamptz default now()
);

create table if not exists food_items (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 name text not null,
 serving text,
 calories numeric default 0,
 protein_g numeric default 0,
 carbs_g numeric default 0,
 fat_g numeric default 0,
 created_at timestamptz default now()
);

create table if not exists meal_logs (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 food_id uuid references food_items(id) on delete set null,
 meal_date date default current_date,
 meal_type text default 'Other',
 quantity numeric default 1,
 calories numeric default 0,
 protein_g numeric default 0,
 carbs_g numeric default 0,
 fat_g numeric default 0,
 created_at timestamptz default now()
);

create table if not exists body_progress (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references profiles(id) on delete cascade,
 log_date date default current_date,
 weight_kg numeric,
 steps integer,
 water_ml integer,
 sleep_hours numeric,
 notes text,
 created_at timestamptz default now()
);

create table if not exists announcements (
 id uuid primary key default gen_random_uuid(),
 title text not null,
 body text not null,
 created_by uuid references profiles(id) on delete set null,
 created_at timestamptz default now()
);

create index if not exists idx_profiles_activity on profiles(last_activity);
create index if not exists idx_habits_user on habits(user_id);
create index if not exists idx_habit_logs_user_date on habit_logs(user_id,log_date);
create index if not exists idx_workouts_user_date on workouts(user_id,workout_date);
create index if not exists idx_food_user on food_items(user_id);
create index if not exists idx_meals_user_date on meal_logs(user_id,meal_date);
create index if not exists idx_progress_user_date on body_progress(user_id,log_date);
