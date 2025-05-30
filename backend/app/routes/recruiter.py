from flask import Blueprint, jsonify, request
from app import db
from app.models.user import User
from app.models.job import JobDescription
from app.models.skill import Skill
from datetime import datetime
from app.services import question_batches

recruiter_bp = Blueprint('recruiter', __name__)

# Fetch past and active assessments
@recruiter_bp.route('/assessments', methods=['GET'])
def get_assessments():
    # Temporarily hardcode recruiter_id for testing (replace with session['user_id'] after login is implemented)
    recruiter_id = 1
    current_time = datetime.utcnow()

    # Fetch jobs (assessments) for the recruiter
    jobs = JobDescription.query.filter_by(recruiter_id=recruiter_id).all()

    # Categorize into past and active assessments
    past_assessments = []
    active_assessments = []
    for job in jobs:
        assessment = {
            'id': job.job_id,
            'test_name': job.job_title,
            'company': job.company,
            'schedule': job.schedule.isoformat(),
            'num_questions': job.num_questions,
            'duration': job.duration,
            'experience_min': job.experience_min,
            'experience_max': job.experience_max,
            'skills': [{'name': skill.skill.name, 'priority': skill.priority} for skill in job.required_skills]
        }
        if job.schedule < current_time:
            past_assessments.append(assessment)
        else:
            active_assessments.append(assessment)

    return jsonify({
        'past_assessments': past_assessments,
        'active_assessments': active_assessments
    })

# Create a new assessment
@recruiter_bp.route('/assessments', methods=['POST'])
def create_assessment():from flask import Blueprint, jsonify
from app import db
from app.models.job import JobDescription
from app.models.assessment_registration import AssessmentRegistration
from app.models.candidate import Candidate
from app.models.required_skill import RequiredSkill
from app.models.candidate_skill import CandidateSkill
from app.models.skill import Skill
from sqlalchemy import and_

recruiter_api_bp = Blueprint('recruiter_api', __name__, url_prefix='/api/recruiter')

@recruiter_api_bp.route('/assessments/<int:recruiter_id>', methods=['GET'])
def get_assessments(recruiter_id):
    assessments = JobDescription.query.filter_by(recruiter_id=recruiter_id).all()
    return jsonify([{
        'job_id': assessment.job_id,
        'job_title': assessment.job_title,
        'company': assessment.company,
        'experience_min': assessment.experience_min,
        'experience_max': assessment.experience_max,
        'duration': assessment.duration,
        'num_questions': assessment.num_questions,
        'schedule': assessment.schedule.isoformat() if assessment.schedule else None,
        'required_degree': assessment.degree_required,
        'description': assessment.description
    } for assessment in assessments]), 200

@recruiter_api_bp.route('/candidates/<int:job_id>', methods=['GET'])
def get_ranked_candidates(job_id):
    # Fetch job details
    job = JobDescription.query.get_or_404(job_id)
    
    # Fetch registered candidates
    registrations = AssessmentRegistration.query.filter_by(job_id=job_id).all()
    candidate_ids = [r.candidate_id for r in registrations]
    candidates = Candidate.query.filter(Candidate.candidate_id.in_(candidate_ids)).all()
    
    # Fetch required skills for the job
    required_skills = RequiredSkill.query.filter_by(job_id=job_id).all()
    required_skill_dict = {
        rs.skill_id: rs.priority for rs in required_skills
    }
    
    # Fetch candidate skills
    candidate_skills = CandidateSkill.query.filter(
        and_(
            CandidateSkill.candidate_id.in_(candidate_ids),
            CandidateSkill.skill_id.in_(required_skill_dict.keys())
        )
    ).all()
    
    # Organize candidate skills
    candidate_skill_map = {}
    for cs in candidate_skills:
        if cs.candidate_id not in candidate_skill_map:
            candidate_skill_map[cs.candidate_id] = {}
        candidate_skill_map[cs.candidate_id][cs.skill_id] = cs.proficiency
    
    # Calculate maximum possible skill score
    max_proficiency = 8  # As per parsing.py (advanced=8)
    max_skill_score = sum(required_skill_dict.values()) * max_proficiency
    
    # Rank candidates
    ranked_candidates = []
    for candidate in candidates:
        # Skill match score
        skill_score = 0
        matched_skills = []
        for skill_id, priority in required_skill_dict.items():
            proficiency = candidate_skill_map.get(candidate.candidate_id, {}).get(skill_id, 0)
            if proficiency > 0:
                skill_name = Skill.query.get(skill_id).name
                matched_skills.append(f"{skill_name} (Proficiency: {proficiency})")
                skill_score += priority * proficiency
        
        skill_score_normalized = skill_score / max_skill_score if max_skill_score > 0 else 0
        
        # Experience score
        exp_midpoint = (job.experience_min + job.experience_max) / 2
        exp_range = job.experience_max - job.experience_min
        exp_diff = abs(candidate.years_of_experience - exp_midpoint)
        exp_score = max(0, 1 - (exp_diff / (exp_range / 2))) if exp_range > 0 else 1
        
        # Total score
        total_score = (0.7 * skill_score_normalized) + (0.3 * exp_score)
        
        # Generate rank description
        description = f"{candidate.name} is ranked based on "
        if matched_skills:
            description += f"strong skills in {', '.join(matched_skills)}"
        else:
            description += "limited skill matches"
        description += f" and {candidate.years_of_experience} years of experience, which "
        if exp_diff < 0.5:
            description += "closely matches"
        elif exp_diff < 1.5:
            description += "reasonably matches"
        else:
            description += "is outside"
        description += f" the job's {job.experience_min}-{job.experience_max} year requirement."
        
        ranked_candidates.append({
            'candidate_id': candidate.candidate_id,
            'name': candidate.name,
            'email': candidate.email,
            'total_score': round(total_score, 2),
            'skill_score': round(skill_score_normalized, 2),
            'experience_score': round(exp_score, 2),
            'description': description
        })
    
    # Sort by total score (descending)
    ranked_candidates.sort(key=lambda x: x['total_score'], reverse=True)
    
    # Add rank numbers
    for i, candidate in enumerate(ranked_candidates, 1):
        candidate['rank'] = i
    
    return jsonify({
        'job_id': job_id,
        'job_title': job.job_title,
        'candidates': ranked_candidates
    }), 200
    data = request.json
    # Temporarily hardcode recruiter_id for testing (replace with session['user_id'] after login is implemented)
    recruiter_id = 1

    # Validate required fields
    required_fields = ['test_name', 'skills', 'experience_min', 'experience_max', 
                       'duration', 'num_questions', 'schedule']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate skills format
    if not isinstance(data['skills'], list) or not all('name' in skill and 'priority' in skill for skill in data['skills']):
        return jsonify({"error": "Skills must be a list of objects with 'name' and 'priority'"}), 400

    try:
        # Parse schedule
        schedule = datetime.fromisoformat(data['schedule'].replace('Z', '+00:00'))

        # Create new job description
        job = JobDescription(
            recruiter_id=recruiter_id,
            job_title=data['test_name'],
            company=data.get('company', ''),
            location=data.get('location'),
            experience_min=data['experience_min'],
            experience_max=data['experience_max'],
            degree_required=data.get('required_degree'),
            description=data.get('description'),
            duration=data['duration'],
            num_questions=data['num_questions'],
            schedule=schedule
        )
        db.session.add(job)
        db.session.flush()  # Get job.job_id before committing

        # Add skills (create new skills if they don't exist)
        for skill_data in data['skills']:
            # Map priority (low: 1-2, medium: 3, high: 4-5)
            priority_map = {'low': 2, 'medium': 3, 'high': 5}
            priority = priority_map.get(skill_data['priority'].lower())
            if not priority:
                raise ValueError(f"Invalid priority: {skill_data['priority']}. Must be 'low', 'medium', or 'high'.")

            # Check if skill exists, otherwise create it
            skill = Skill.query.filter_by(name=skill_data['name']).first()
            if not skill:
                skill = Skill(name=skill_data['name'], category='technical')
                db.session.add(skill)
                db.session.flush()

            required_skill = RequiredSkill(
                job_id=job.job_id,
                skill_id=skill.skill_id,
                priority=priority
            )
            db.session.add(required_skill)

        db.session.commit()

        # Trigger question generation
        try:
            skills_with_priorities = [
                {"name": skill_data['name'], "priority": priority_map[skill_data['priority'].lower()]}
                for skill_data in data['skills']
            ]
            jd_experience_range = f"{data['experience_min']}-{data['experience_max']}"
            question_batches.prepare_question_batches(skills_with_priorities, jd_experience_range, job.job_id)
        except Exception as e:
            print(f"⚠️ Error generating questions: {e}")
            # Continue even if question generation fails (assessment is still created)
            pass

        return jsonify({"message": "Assessment created successfully", "job_id": job.job_id}), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500