from flask import Blueprint, request, jsonify
from models import db, Group, Membership, User

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/groups/<int:group_id>/join', methods=['POST'])
def join_group(group_id):
    # In a real app, get this from your session/token
    current_student_id = 1 
    
    # 1. Check if group exists
    group = Group.query.get_or_404(group_id)
    
    # 2. Check if already a member
    existing = Membership.query.filter_by(
        student_id=current_student_id, 
        group_id=group_id
    ).first()
    
    if existing:
        return jsonify({"error": "Already a member"}), 400
    
    # 3. Add membership
    new_member = Membership(student_id=current_student_id, group_id=group_id, role=1)
    db.session.add(new_member)
    
    # 4. TODO: Add "System Message" for Role 6 (Chat)
    
    db.session.commit()
    return jsonify({"message": f"Successfully joined {group.name}"}), 201