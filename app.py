import os
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from supabase_client import get_supabase
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")
supabase = get_supabase()

# --- Helpers ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Unauthorized access.", "error")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# --- Routes ---
@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password,
            })

            if auth_response.user:
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
            else:
                flash("Registration failed.", "error")
        except Exception as e:
            flash(f"Error: {str(e)}", "error")

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if auth_response.user:
                try:
                    user_query = supabase.table("users", token=auth_response.access_token).select("role").eq("id", auth_response.user.id).execute()
                    user_data_list = user_query.data if isinstance(user_query.data, list) else []

                    if not user_data_list:
                        print(f"User {auth_response.user.id} not found in public.users, creating...")
                        supabase.table("users", token=auth_response.access_token).insert({
                            "id": auth_response.user.id,
                            "email": auth_response.user.email,
                            "role": "user"
                        }).execute()
                        role = "user"
                    else:
                        role = user_data_list[0].get('role', 'user')
                except Exception as e:
                    print(f"User check/init failed: {e}")
                    role = "user"

                session['user'] = {
                    "id": auth_response.user.id,
                    "email": auth_response.user.email,
                    "access_token": auth_response.access_token
                }
                session['role'] = role

                flash(f"Welcome back, {email}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid credentials.", "error")
        except Exception as e:
            error_str = str(e)
            if "Email not confirmed" in error_str:
                flash("Login failed: Please confirm your email or disable 'Confirm Email' in Supabase Auth settings.", "error")
            else:
                flash(f"Login failed: {error_str}", "error")
            print(f"Login Error: {error_str}")

    return render_template('login.html')

@app.route('/logout')
def logout():
    supabase.auth.sign_out()
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    token = session['user'].get('access_token')
    courses_query = supabase.table("courses", token=token).select("*").execute()
    courses = courses_query.data or []
    return render_template('dashboard.html', courses=courses)

# ============================================================
# ADMIN — Courses
# ============================================================

@app.route('/admin')
@login_required
@admin_required
def admin():
    token = session['user'].get('access_token')
    courses_query = supabase.table("courses", token=token).select("*").execute()
    courses = courses_query.data or []
    return render_template('admin.html', courses=courses)

@app.route('/admin/course/create', methods=['POST'])
@login_required
@admin_required
def create_course():
    title = request.form.get('title')
    description = request.form.get('description')
    youtube_url = request.form.get('youtube_url')

    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    video_id = video_id_match.group(1) if video_id_match else None

    if not video_id:
        flash("Invalid YouTube URL.", "error")
        return redirect(url_for('admin'))

    token = session['user'].get('access_token')
    try:
        supabase.table("courses", token=token).insert({
            "title": title,
            "description": description,
            "created_by": session['user']['id']
        }).execute()

        new_course = supabase.table("courses", token=token).select("id").eq("title", title).order("created_at", desc=True).limit(1).execute()
        if new_course.data:
            supabase.table("course_videos", token=token).insert({
                "course_id": new_course.data[0]['id'],
                "youtube_url": youtube_url,
                "youtube_video_id": video_id
            }).execute()

        flash("Course created successfully!", "success")
    except Exception as e:
        flash(f"Error creating course: {str(e)}", "error")

    return redirect(url_for('admin'))

@app.route('/admin/course/delete/<course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    token = session['user'].get('access_token')
    try:
        supabase.table("courses", token=token).delete().eq("id", course_id).execute()
        flash("Course deleted.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")
    return redirect(url_for('admin'))

# ============================================================
# ADMIN — Quiz Questions
# ============================================================

@app.route('/admin/quiz')
@login_required
@admin_required
def admin_quiz():
    token = session['user'].get('access_token')
    course_id = request.args.get('course_id')

    # All courses for filter bar
    courses_query = supabase.table("courses", token=token).select("*").execute()
    courses = courses_query.data or []

    # Questions — filtered by course if provided
    q_builder = supabase.table("quiz_questions", token=token).select("*").order("created_at", desc=True)
    if course_id:
        q_builder = q_builder.eq("course_id", course_id)
    questions_query = q_builder.execute()
    questions = questions_query.data or []

    # Selected course object
    selected_course = None
    if course_id:
        for c in courses:
            if c['id'] == course_id:
                selected_course = c
                break

    # Unique subjects
    subjects = list({q['subject'] for q in questions if q.get('subject')})

    # Count total attempts
    try:
        attempts_query = supabase.table("quiz_attempts", token=token).select("id").execute()
        attempt_count = len(attempts_query.data or [])
    except Exception:
        attempt_count = 0

    return render_template(
        'admin_quiz.html',
        questions=questions,
        courses=courses,
        selected_course=selected_course,
        subjects=subjects,
        attempt_count=attempt_count
    )


@app.route('/admin/quiz/create', methods=['POST'])
@login_required
@admin_required
def create_quiz_question():
    token = session['user'].get('access_token')
    course_id = request.form.get('course_id') or None
    subject   = request.form.get('subject', '').strip()
    question  = request.form.get('question', '').strip()
    option_a  = request.form.get('option_a', '').strip()
    option_b  = request.form.get('option_b', '').strip()
    option_c  = request.form.get('option_c', '').strip()
    option_d  = request.form.get('option_d', '').strip()
    correct   = request.form.get('correct_answer', '').strip().upper()

    if not all([subject, question, option_a, option_b, option_c, option_d, correct]):
        flash("All fields are required.", "error")
        return redirect(url_for('admin_quiz') + (f'?course_id={course_id}' if course_id else ''))

    if correct not in ('A', 'B', 'C', 'D'):
        flash("Correct answer must be A, B, C, or D.", "error")
        return redirect(url_for('admin_quiz') + (f'?course_id={course_id}' if course_id else ''))

    try:
        payload = {
            "subject":        subject,
            "question":       question,
            "option_a":       option_a,
            "option_b":       option_b,
            "option_c":       option_c,
            "option_d":       option_d,
            "correct_answer": correct,
            "created_by":     session['user']['id']
        }
        if course_id:
            payload["course_id"] = course_id

        supabase.table("quiz_questions", token=token).insert(payload).execute()
        flash("Question added successfully!", "success")
    except Exception as e:
        flash(f"Error adding question: {str(e)}", "error")

    redirect_url = url_for('admin_quiz')
    if course_id:
        redirect_url += f'?course_id={course_id}'
    return redirect(redirect_url)


@app.route('/admin/quiz/delete/<question_id>', methods=['POST'])
@login_required
@admin_required
def delete_quiz_question(question_id):
    token = session['user'].get('access_token')
    course_id = request.form.get('course_id')
    try:
        supabase.table("quiz_questions", token=token).delete().eq("id", question_id).execute()
        flash("Question deleted.", "success")
    except Exception as e:
        flash(f"Error: {str(e)}", "error")

    redirect_url = url_for('admin_quiz')
    if course_id:
        redirect_url += f'?course_id={course_id}'
    return redirect(redirect_url)

# ============================================================
# COURSES — View
# ============================================================

@app.route('/course/<course_id>')
@login_required
def view_course(course_id):
    token = session['user'].get('access_token')
    course_query = supabase.table("courses", token=token).select("*").eq("id", course_id).single().execute()
    video_query  = supabase.table("course_videos", token=token).select("*").eq("course_id", course_id).single().execute()

    if not course_query.data:
        flash("Course not found.", "error")
        return redirect(url_for('dashboard'))

    video_id = video_query.data['youtube_video_id'] if video_query.data else ""

    # Fetch quiz questions — course-specific first, fall back to general pool
    try:
        q_query = supabase.table("quiz_questions", token=token).select("*").eq("course_id", course_id).order("created_at").execute()
        questions = q_query.data or []
        if not questions:
            all_q = supabase.table("quiz_questions", token=token).select("*").order("created_at").execute()
            questions = [q for q in (all_q.data or []) if not q.get('course_id')]
    except Exception:
        questions = []

    return render_template('course.html', course=course_query.data, video_id=video_id, questions=questions)

# ============================================================
# QUIZ — User Quiz Page
# ============================================================

@app.route('/course/<course_id>/quiz')
@login_required
def quiz(course_id):
    token = session['user'].get('access_token')

    # Get course
    try:
        course_query = supabase.table("courses", token=token).select("*").eq("id", course_id).single().execute()
        if not course_query.data:
            flash("Course not found.", "error")
            return redirect(url_for('dashboard'))
        course = course_query.data
    except Exception as e:
        flash(f"Error loading course: {str(e)}", "error")
        return redirect(url_for('dashboard'))

    # Questions: prefer course-specific, fall back to general (no course_id)
    try:
        questions_query = supabase.table("quiz_questions", token=token).select("*").eq("course_id", course_id).order("created_at").execute()
        questions = questions_query.data or []

        if not questions:
            all_q_query = supabase.table("quiz_questions", token=token).select("*").order("created_at").execute()
            all_q = all_q_query.data or []
            questions = [q for q in all_q if not q.get('course_id')]
    except Exception as e:
        questions = []
        flash(f"Error loading questions: {str(e)}", "error")

    return render_template('quiz.html', course=course, questions=questions)

# ============================================================
# API — Emotion Logging
# ============================================================

@app.route('/api/log_emotion', methods=['POST'])
@login_required
def log_emotion():
    data = request.json
    token = session['user'].get('access_token')
    try:
        supabase.table("emotion_logs", token=token).insert({
            "user_id":          session['user']['id'],
            "course_id":        data.get('course_id'),
            "emotion":          data.get('emotion'),
            "confidence_score": data.get('score'),
            "video_timestamp":  data.get('timestamp')
        }).execute()
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================================
# API — Submit Quiz Answer (with Emotion)
# ============================================================

@app.route('/api/submit_quiz_answer', methods=['POST'])
@login_required
def submit_quiz_answer():
    data  = request.json
    token = session['user'].get('access_token')

    question_id     = data.get('question_id')
    course_id       = data.get('course_id')
    selected_answer = (data.get('selected_answer') or '').upper()
    emotion         = data.get('emotion', 'neutral')
    confidence      = data.get('confidence_score', 0.0)

    if not question_id or not selected_answer:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Fetch the correct answer for this question
        q_query = supabase.table("quiz_questions", token=token).select("correct_answer").eq("id", question_id).single().execute()
        if not q_query.data:
            return jsonify({"error": "Question not found"}), 404

        correct_answer = q_query.data['correct_answer']
        is_correct     = (selected_answer == correct_answer)

        # Store attempt with emotion
        supabase.table("quiz_attempts", token=token).insert({
            "user_id":          session['user']['id'],
            "course_id":        course_id,
            "question_id":      question_id,
            "selected_answer":  selected_answer,
            "is_correct":       is_correct,
            "emotion":          emotion,
            "confidence_score": confidence
        }).execute()

        return jsonify({
            "is_correct":     is_correct,
            "correct_answer": correct_answer,
            "emotion":        emotion
        }), 200

    except Exception as e:
        print(f"submit_quiz_answer error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
