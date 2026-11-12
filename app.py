
from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)


# Home API
@app.route("/")
def home():
    return "Welcome to StoryBook Learning!"


# Health Check API
@app.route("/api/health")
def health():
    return jsonify({
        "status": "success",
        "message": "StoryBook Backend is working!"
    })


# Student Registration API
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({
            "status": "error",
            "message": "All fields are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "status": "error",
            "message": "Password must contain at least 8 characters"
        }), 400

    hashed_password = generate_password_hash(password)
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT student_id FROM students WHERE email = %s",
            (email,)
        )

        if cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Email already registered"
            }), 409

        cursor.execute(
            "INSERT INTO students (student_name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Student registered successfully!"
        }), 201

    except Exception as e:
        print("REGISTRATION ERROR:", repr(e))
        if conn:
            conn.rollback()

        return jsonify({
            "status": "error",
            "message": "Registration failed. Please try again."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# Student Login API
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "status": "error",
            "message": "Email and password are required"
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT student_id, student_name, email, password FROM students WHERE email = %s",
            (email,)
        )

        student = cursor.fetchone()

        if student and check_password_hash(student["password"], password):
            return jsonify({
                "status": "success",
                "message": "Login successful!",
                "student": {
                    "student_id": student["student_id"],
                    "student_name": student["student_name"],
                    "email": student["email"]
                }
            }), 200

        return jsonify({
            "status": "error",
            "message": "Invalid email or password"
        }), 401

    except Exception as e:
        print("LOGIN ERROR:", repr(e))
        return jsonify({
            "status": "error",
            "message": "Login failed. Please try again."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route("/api/student/<int:student_id>", methods=["GET"])
def get_student(student_id):
    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT student_id, student_name, email, created_at FROM students WHERE student_id = %s",
            (student_id,)
        )

        student = cursor.fetchone()

        if student:
            return jsonify({
                "status": "success",
                "student": student
            }), 200

        return jsonify({
            "status": "error",
            "message": "Student not found"
        }), 404

    except Exception as e:
        print("Profile Error:", e)
        return jsonify({
            "status": "error",
            "message": "Something went wrong"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# Get All Lessons API
@app.route("/api/lessons", methods=["GET"])
def get_lessons():
    conn = None
    cursor = None

    try:
        subject = request.args.get("subject")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if subject:
            cursor.execute(
                "SELECT * FROM lessons WHERE subject = %s",
                (subject,)
            )
        else:
            cursor.execute("SELECT * FROM lessons")

        lessons = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total_lessons": len(lessons),
            "lessons": lessons
        }), 200

    except Exception as e:
        print("LESSONS ERROR:", repr(e))
        return jsonify({
            "status": "error",
            "message": "Unable to fetch lessons"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Get Quiz Questions API
@app.route("/api/quiz-questions", methods=["GET"])
def get_quiz_questions():
    conn = None
    cursor = None

    try:
        subject = request.args.get("subject")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if subject:
            cursor.execute(
                """
                SELECT question_id, subject, question,
                       option_a, option_b, option_c, option_d
                FROM quiz_questions
                WHERE subject = %s
                """,
                (subject,)
            )
        else:
            cursor.execute(
                """
                SELECT question_id, subject, question,
                       option_a, option_b, option_c, option_d
                FROM quiz_questions
                """
            )

        questions = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total_questions": len(questions),
            "questions": questions
        }), 200

    except Exception as e:
        print("QUIZ ERROR:", repr(e))
        return jsonify({
            "status": "error",
            "message": "Unable to fetch quiz questions"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Save Quiz Score API

@app.route("/api/save-score", methods=["POST"])
def save_score():
    data = request.get_json(silent=True) or {}

    student_id = data.get("student_id")
    subject = data.get("subject")
    score = data.get("score")
    total = data.get("total")

    if not student_id or not subject or total is None or score is None:
        return jsonify({
            "status": "error",
            "message": "Student ID, subject, score and total are required"
        }), 400

    try:
        student_id = int(student_id)
        score = int(score)
        total = int(total)

        if total <= 0 or score < 0 or score > total:
            raise ValueError("Invalid score")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT student_id FROM students WHERE student_id = %s",
            (student_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "status": "error",
                "message": "Student not found"
            }), 404

        percentage = round((score / total) * 100)

        cursor.execute(
            """
            INSERT INTO scores
            (student_id, subject, total_questions, correct_answers, score)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (student_id, subject, total, score, percentage)
        )

        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Quiz score saved successfully!",
            "score": score,
            "total": total,
            "percentage": percentage
        }), 201

    except ValueError as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

    except Exception as e:
        print("SCORE ERROR:", repr(e))

        if 'conn' in locals():
            conn.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to save score"
        }), 500

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn and conn.is_connected():
            conn.close()

# Student Score History API
@app.route("/api/student/<int:student_id>/scores", methods=["GET"])
def get_student_scores(student_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT score_id, student_id, subject,
                   total_questions, correct_answers, score
            FROM scores
            WHERE student_id = %s
            ORDER BY score_id DESC
            """,
            (student_id,)
        )

        scores = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total_attempts": len(scores),
            "scores": scores
        }), 200

    except Exception as e:
        print("SCORE HISTORY ERROR:", repr(e))
        return jsonify({
            "status": "error",
            "message": "Unable to fetch student scores"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Student Profile API

@app.route("/api/profile", methods=["GET", "POST"])
def student_profile():
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Create profile table if it does not exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_profiles (
                student_id INT PRIMARY KEY,
                name VARCHAR(70) NOT NULL,
                course VARCHAR(90),
                college VARCHAR(120),
                semester VARCHAR(60),
                email VARCHAR(120),
                goal VARCHAR(100),
                about TEXT
            )
        """)

        if request.method == "POST":
            data = request.get_json(silent=True) or {}

            student_id = data.get("student_id")
            name = data.get("name", "").strip()

            if not student_id or not name:
                return jsonify({
                    "status": "error",
                    "message": "Student ID and name are required"
                }), 400

            cursor.execute(
                "SELECT student_id FROM students WHERE student_id = %s",
                (student_id,)
            )

            if not cursor.fetchone():
                return jsonify({
                    "status": "error",
                    "message": "Student not found"
                }), 404

            cursor.execute("""
                INSERT INTO student_profiles
                (student_id, name, course, college, semester, email, goal, about)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                course = VALUES(course),
                college = VALUES(college),
                semester = VALUES(semester),
                email = VALUES(email),
                goal = VALUES(goal),
                about = VALUES(about)
            """, (
                student_id,
                name,
                data.get("course", ""),
                data.get("college", ""),
                data.get("semester", ""),
                data.get("email", ""),
                data.get("goal", ""),
                data.get("about", "")
            ))

            conn.commit()

            return jsonify({
                "status": "success",
                "message": "Student profile saved successfully!"
            }), 200

        # GET profile
        student_id = request.args.get("student_id")

        if not student_id:
            return jsonify({
                "status": "error",
                "message": "Student ID is required"
            }), 400

        cursor.execute(
            "SELECT * FROM student_profiles WHERE student_id = %s",
            (student_id,)
        )

        profile = cursor.fetchone()

        return jsonify({
            "status": "success",
            "profile": profile
        }), 200

    except Exception as e:
        print("PROFILE API ERROR:", repr(e))

        if conn:
            conn.rollback()

        return jsonify({
            "status": "error",
            "message": "Unable to process student profile"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Run Flask Server
if __name__ == "__main__":
    app.run(debug=True)
