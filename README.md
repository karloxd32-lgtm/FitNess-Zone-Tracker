# Fitness Zone Tracker — A to Z project

**Name:** Fitness Zone Tracker
**Made By:** Aditya Chaudhary
**Owner email:** fitness.zone.tracker@gmail.com

## Stack
Vercel + Python FastAPI + Supabase PostgreSQL + Gmail SMTP.

## Features included
- Signup with email OTP verification
- Normal email/password login (no OTP)
- Forgot password with email OTP
- Reset password with confirmation
- User dashboard
- Habits with custom user-created habits
- Gym workout logging
- Exercises, sets/reps/weight database
- Personal food database
- Daily meal logging
- Calories/macros
- Weight, steps, water and sleep progress
- User settings schema
- Admin panel
- Owner panel
- Total / active / offline users
- Ban/unban
- Owner can promote/demote admins
- Announcements
- Responsive phone/desktop UI
- Server-side authorization
- Password hashing
- Supabase PostgreSQL schema
- Vercel deployment configuration

## Deploy
1. Create a Supabase project.
2. Open Supabase SQL Editor and run `supabase/schema.sql`.
3. Upload this project to a GitHub repository.
4. Import that repository into Vercel.
5. Add the variables from `.env.example` to Vercel Environment Variables.
6. For Gmail OTP, create a Google App Password for the dedicated sender account and put it only in `SMTP_APP_PASSWORD`.
7. Deploy.

The desired URL is `fitness.vercel.app` if that Vercel project hostname is available. Otherwise Vercel will assign another `*.vercel.app` hostname.

## Important
Do not put the Supabase service-role key, Gmail app password, JWT secret, or any other secret in `public/` or in frontend JavaScript.

Before public launch, also enable rate limiting/CAPTCHA and review production security policies.
