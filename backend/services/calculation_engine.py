"""
ResultCloud calculation engine.

Extracted from PyGPA-Analyzer (reference/source_code.py and reference/app.py).
The academic logic is kept exactly as in the reference, including its quirks.
See NOTES in README.md before changing anything here.
"""
import random

# ---------------------------------------------------------------- config
# Credits format: [credit of each subject..., total semester credit]
# Exam type format: [no. of subjects with TEE, no. of ICA-only subjects]

CSDS_SUBJECTS = {
    'sem1': ['Calculus', 'Programming for Problem Solving', 'Basic Electrical and Electronics Engineering', 'Engineering Graphics and Design', 'Elements of Biology', 'English Communication', 'Professional Ethics', 'Constitution of India', 'Design Thinking'],
    'sem2': ['Linear Algebra and Differential Equations', 'Physics', 'Digital Circuits and Computer Architecture', 'Principles of Economics and Management', 'Python for data analysis', 'Environmental Science', 'Digital Manufacturing Laboratory', 'Electrical and Electronics Workshop', 'Critical Thinking'],
    'sem3': ['Optimization methods', 'Data Structures and Algorithms', 'Probability and Statistics', 'Data Wrangling', 'Discrete Mathematics', 'Management Accounting for Engineers', 'Technical Communication', 'Community service'],
    'sem4': ['Machine learning', 'Introduction to Data, Signal, and Image Analysis', 'Statistical Methods', 'Database Management Systems', 'Web Programming', 'Data handling and Visualization'],
    'sem5': ['Software Engineering', 'Computer Networks', 'Operating Systems', 'Department Elective I', 'Open Elective I', 'Open Elective II', 'Mobile Application development'],
    'sem6': ['Applied Artificial Intelligence', 'Neural Networks and Deep Learning', 'Advance Data Structure for Analytics', 'Department Elective II', 'Department Elective III', 'Open Elective III', 'Open Elective IV ', 'Interpersonal Skills'],
    'sem7': ['Cloud Computing', 'Big Data', 'Computer Vision', 'Department Elective IV', 'Department Elective V', 'Open Elective V', 'Capstone Project'],
    'sem8': ['Project'],
}

CSDS_CREDITS = {
    'sem1': [4, 4, 3, 3, 3, 1, 1, 0, 0, 19],
    'sem2': [4, 4, 4, 3, 2, 2, 1, 1, 0, 21],
    'sem3': [4, 4, 3, 3, 3, 2, 1, 0, 20],
    'sem4': [4, 4, 3, 3, 3, 2, 19],
    'sem5': [3, 3, 3, 3, 3, 3, 3, 21],
    'sem6': [4, 3, 3, 3, 3, 3, 3, 1, 23],
    'sem7': [4, 3, 3, 3, 3, 3, 3, 22],
    'sem8': [10, 10],
}

CSDS_EXAM_TYPE = {
    'sem1': [5, 4], 'sem2': [5, 4], 'sem3': [6, 2], 'sem4': [6, 0],
    'sem5': [6, 1], 'sem6': [7, 1], 'sem7': [6, 1], 'sem8': [0, 1],
}

CE_SUBJECTS = {
    'sem1': ['Calculus', 'Programming for Problem Solving', 'Physics', 'Elements of Biology', 'Engineering Graphics and Design', 'Professional Ethics', 'Constitution of India', 'Critical Thinking'],
    'sem2': ['Linear Algebra and Differential Equations', 'Basic Electrical and Electronics Engineering', 'Quantum and Statistical Physics', 'Management Accounting for Engineers', 'Python Programming', 'Environmental Science', 'English Communication', 'Digital Manufacturing Laboratory', 'Electrical and Electronics Workshop', 'Design Thinking'],
    'sem3': ['Data Structures and Algorithms', 'Probability and Statistics', 'Discrete Mathematics', 'Principles of Economics and Management', 'Digital Logic Design', 'Computer Networks', 'Data Extraction and Processing', 'Technical Communication', 'Community service'],
    'sem4': ['Complex Variables and Transforms', 'Microprocessor and Microcontroller', 'Computer Organization and Architecture', 'Design and Analysis of Algorithm', 'Database Management Systems', 'Theoretical Computer Science', 'Web Programming', 'Object Oriented Programming through JAVA'],
    'sem5': ['Software Engineering', 'Artificial Intelligence', 'Operating Systems', 'Image and Video Processing', 'Department Elective I', 'Open Elective I', 'Open Elective II'],
    'sem6': ['Cyber Security', 'Distributed Computing', 'Machine Learning', 'Department Elective II', 'Department Elective III', 'Open Elective III', 'Open Elective IV ', 'Interpersonal Skills'],
    'sem7': ['Cloud Computing', 'Department Elective IV', 'Department Elective V', 'Department Elective VI', 'Open Elective V', 'Capstone Project'],
    'sem8': ['Project'],
}

CE_CREDITS = {
    'sem1': [4, 4, 4, 3, 3, 1, 0, 0, 19],
    'sem2': [4, 3, 3, 2, 2, 1, 1, 1, 1, 0, 18],
    'sem3': [4, 3, 3, 3, 3, 3, 2, 1, 0, 22],
    'sem4': [4, 4, 3, 3, 3, 3, 3, 1, 24],
    'sem5': [3, 3, 3, 3, 3, 3, 3, 21],
    'sem6': [3, 3, 3, 3, 3, 3, 3, 1, 22],
    'sem7': [3, 3, 3, 3, 3, 4, 19],
    'sem8': [10, 10],
}

CE_EXAM_TYPE = {
    'sem1': [5, 3], 'sem2': [5, 5], 'sem3': [6, 3], 'sem4': [7, 1],
    'sem5': [7, 0], 'sem6': [7, 1], 'sem7': [5, 1], 'sem8': [0, 1],
}

# NOTE: source_code.py gives CE students the CSDS credits; app.py gives them
# CE credits. The brief says keep the source_code.py behaviour, so this stays
# True. With True, CE sem2/3/4 have more subjects than credits and fail,
# same as the reference. See README "Open questions".
CE_USES_CSDS_CREDITS = True

# 1.15 (D) is not a key here, same as the reference. See README.
GRADE_SCALE_4 = {4: 'A+', 3.75: 'A', 3.5: 'A-', 3.25: 'B+', 3: 'B', 2.75: 'B-', 2.5: 'C+', 2.25: 'C', 2: 'C-', 1.5: 'D', 0: 'F'}
GRADE_SCALE_10 = {10: 'O', 9: 'A+', 8: 'A', 7: 'B+', 6: 'B', 5: 'C', 4: 'P', 0: 'F'}

LOW_MARKS = {
    'old': [85, 81, 77, 73, 69, 65, 61, 57, 50, 40, 0],
    'new': [90, 80, 70, 60, 55, 50, 40, 0],
}


# ---------------------------------------------------------------- sap id
def validate_sap_id(sap_id):
    """Returns (is_valid, category, department)."""
    if len(sap_id) != 11 or not sap_id.isdigit():
        return False, None, None

    first_digits = sap_id[:4]
    if first_digits == "7057":
        category = "old" if sap_id[:6] in ["705722", "705723"] else "new"
        department = "csds"
    elif first_digits == "7002":
        category = "old" if sap_id[:6] in ["700222", "700223"] else "new"
        department = "ce"
    else:
        return False, None, None

    return True, category, department


def get_department_config(department):
    """Returns (exam_type, subjects, credits)."""
    if department == "csds":
        return CSDS_EXAM_TYPE, CSDS_SUBJECTS, CSDS_CREDITS
    credits = CSDS_CREDITS if CE_USES_CSDS_CREDITS else CE_CREDITS
    return CE_EXAM_TYPE, CE_SUBJECTS, credits


def get_grade_config(category):
    """Returns (low_marks, grade_scale)."""
    if category == "old":
        return LOW_MARKS['old'], GRADE_SCALE_4
    return LOW_MARKS['new'], GRADE_SCALE_10


# ---------------------------------------------------------------- marks
def adjust_marks(ica_marks, tee_marks, tee_sub_count):
    """TEE subjects: TEE / 2. ICA-only subjects: ICA * 2, TEE = 0."""
    tee_adj = [m / 2 for m in tee_marks[:tee_sub_count]] + [0] * (len(ica_marks) - tee_sub_count)
    ica_adj = ica_marks[:tee_sub_count] + [m * 2 for m in ica_marks[tee_sub_count:]]
    return ica_adj, tee_adj


def round_TM(x):
    if x >= 0:
        return int(x + 0.5)
    else:
        return int(x - 0.5)


def cal_total_marks(ica_m, tee_m, tee_sub_count, ica_sub_count):
    return [round_TM(ica_m[k] + tee_m[k]) for k in range(tee_sub_count + ica_sub_count)]


# ---------------------------------------------------------------- grading
def old_grade_point(mark):
    for low, gp in [(85, 4.00), (81, 3.75), (77, 3.50), (73, 3.25), (69, 3.00), (65, 2.75),
                    (61, 2.50), (57, 2.25), (50, 2.00), (40, 1.15)]:
        if mark >= low:
            return gp
    return 0


def new_grade_point(mark):
    for low, gp in [(90, 10), (80, 9), (70, 8), (60, 7), (55, 6), (50, 5), (40, 4)]:
        if mark >= low:
            return gp
    return 0


def cal_gpa(total_m, tee_sub_count, ica_sub_count, sem, category, grade_dict_scale, sem_sub_credits):
    """Returns (gpa, grade labels, sum of credit * grade point)."""
    grade_point = old_grade_point if category == "old" else new_grade_point
    grades_scored = [grade_point(m) for m in total_m]
    labels = [grade_dict_scale.get(g, 'F') for g in grades_scored]

    credits, total_credits = sem_sub_credits[sem][:-1], sem_sub_credits[sem][-1]
    _sum = sum(credits[i] * grades_scored[i] for i in range(tee_sub_count + ica_sub_count))
    return _sum / total_credits, labels, _sum


def calculate_cgpa(previous_sgpas, sgpa, sem_num, sem_sub_credits):
    """Credit weighted over all previous SGPAs + current SGPA (app.py)."""
    num, den = 0, 0
    for prev_num, prev_sgpa in enumerate(previous_sgpas, 1):
        c = sem_sub_credits[f'sem{prev_num}'][-1]
        num += prev_sgpa * c
        den += c
    c = sem_sub_credits[f'sem{sem_num}'][-1]
    num += sgpa * c
    den += c
    return num / den


def calculate_result(sap_id, sem_num, ica_marks, tee_marks, previous_sgpas=()):
    """Full 'Calculate GPA' flow from app.py. tee_marks covers TEE subjects only."""
    ok, category, department = validate_sap_id(sap_id)
    if not ok:
        raise ValueError("Invalid SAP ID")
    exam_type, subjects, credits = get_department_config(department)
    _, scale = get_grade_config(category)
    sem = f'sem{sem_num}'
    tee_count, ica_count = exam_type[sem]

    tee_full = list(tee_marks[:tee_count]) + [0] * ica_count
    ica_adj, tee_adj = adjust_marks(list(ica_marks), tee_full, tee_count)
    final = cal_total_marks(ica_adj, tee_adj, tee_count, ica_count)
    sgpa, labels, _ = cal_gpa(final, tee_count, ica_count, sem, category, scale, credits)

    label_to_point = {v: k for k, v in scale.items()}
    rows = []
    for i, subject in enumerate(subjects[sem][:tee_count + ica_count]):
        gp = label_to_point[labels[i]]
        rows.append({'subject': subject, 'credits': credits[sem][i], 'final_marks': final[i],
                     'grade': labels[i], 'grade_point': gp, 'total': credits[sem][i] * gp})

    cgpa = calculate_cgpa(previous_sgpas, sgpa, sem_num, credits) if sem_num > 1 else None
    return {'department': department, 'category': category, 'semester': sem,
            'rows': rows, 'sgpa': sgpa, 'cgpa': cgpa}


# ---------------------------------------------------------------- goal matrix
def calculate_goal_matrix(ica_marks, low_marks):
    """Rows = TEE subjects, columns = grades. Min TEE needed, '-' if > 100."""
    matrix = []
    for ica in ica_marks:
        row = [max(0, (low - ica) * 2) for low in low_marks]
        matrix.append(['-' if v > 100 else v for v in row])
    return matrix


# ---------------------------------------------------------------- planner
def generate_marks(difficulty):
    if difficulty == "easy":
        ica = random.randint(43, 50)
        tee = random.randint(40, 50)
    elif difficulty == "medium":
        ica = random.randint(35, 43)
        tee = random.randint(35, 43)
    else:
        ica = random.randint(25, 35)
        tee = random.randint(25, 35)
    return ica, tee


def generate_plans(subjects, difficulty_levels, tee_sub_count, ica_sub_count, sem, category, grade_dict_scale, sem_sub_credits):
    # Raw ICA + TEE, no /2 or *2 adjustment - same as the reference.
    plan, icas, tees = [], [], []
    for i in range(len(subjects)):
        ica, tee = generate_marks(difficulty_levels[i])
        icas.append(ica)
        tees.append(tee)
        plan.append({"subject": subjects[i], "ICA": ica, "TEE": tee})

    total_m = cal_total_marks(icas, tees, tee_sub_count, ica_sub_count)
    gpa, _, __ = cal_gpa(total_m, tee_sub_count, ica_sub_count, sem, category, grade_dict_scale, sem_sub_credits)
    return plan, gpa


def generate_multiple_plans(subjects, target_gpa, difficulty_levels, tee_sub_count, ica_sub_count, sem, category, grade_dict_scale, sem_sub_credits, num_plans=4):
    # target_gpa is not used to pick plans, same as the reference.
    plans = []
    for _ in range(num_plans):
        plan, gpa = generate_plans(subjects, difficulty_levels, tee_sub_count, ica_sub_count, sem, category, grade_dict_scale, sem_sub_credits)
        plans.append({"plan": plan, "gpa": round(gpa, 2), "meets_target": gpa >= target_gpa})
    return plans
