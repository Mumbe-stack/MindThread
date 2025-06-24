from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from models import db, User, Post, Comment
from functools import wraps
from flask import request

admin_bp = Blueprint('admin_bp', __name__, url_prefix="/api/admin")


def admin_required(f):
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/posts/<int:post_id>/approve", methods=["PATCH"])
@jwt_required()
@admin_required
def approve_post(post_id):
   
    try:
        post = Post.query.get_or_404(post_id)
        data = request.get_json()

        if "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        post.is_approved = bool(data["is_approved"])
        post.is_flagged = False  
        db.session.commit()

        status = "approved" if post.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Post {status} successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process post: {str(e)}"}), 500


@admin_bp.route("/comments/<int:comment_id>/approve", methods=["PATCH"])
@jwt_required()
@admin_required
def approve_comment(comment_id):
   
    try:
        comment = Comment.query.get_or_404(comment_id)
        data = request.get_json()

        if "is_approved" not in data:
            return jsonify({"error": "Missing 'is_approved' field"}), 400

        comment.is_approved = bool(data["is_approved"])
        comment.is_flagged = False  
        db.session.commit()

        status = "approved" if comment.is_approved else "rejected"
        return jsonify({
            "success": True,
            "message": f"Comment {status} successfully"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to process comment: {str(e)}"}), 500


@admin_bp.route("/posts/<int:post_id>/flag", methods=["PATCH"])
@jwt_required()
@admin_required
def flag_post(post_id):
    
    try:
        post = Post.query.get_or_404(post_id)
        post.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Post flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag post: {str(e)}"}), 500


@admin_bp.route("/comments/<int:comment_id>/flag", methods=["PATCH"])
@jwt_required()
@admin_required
def flag_comment(comment_id):
   
    try:
        comment = Comment.query.get_or_404(comment_id)
        comment.is_flagged = True
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Comment flagged for review"
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to flag comment: {str(e)}"}), 500


@admin_bp.route("/users/search", methods=["GET"])
@jwt_required()
@admin_required
def search_users():
   
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify([]), 200

        users = User.query.filter(
            db.or_(
                User.username.ilike(f'%{query}%'),
                User.email.ilike(f'%{query}%')
            )
        ).limit(20).all()

        return jsonify([{
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "is_admin": u.is_admin,
            "is_blocked": u.is_blocked,
            "created_at": u.created_at.isoformat(),
            "post_count": len(u.posts),
            "comment_count": len(u.comments)
        } for u in users]), 200

    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@admin_bp.route("/content-stats", methods=["GET"])
@jwt_required()
@admin_required
def get_content_stats():
   
    try:
        total_posts = Post.query.count()
        approved_posts = Post.query.filter_by(is_approved=True).count()
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        
        total_comments = Comment.query.count()
        approved_comments = Comment.query.filter_by(is_approved=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        
        total_users = User.query.count()
        admin_users = User.query.filter_by(is_admin=True).count()
        blocked_users = User.query.filter_by(is_blocked=True).count()
        active_users = total_users - blocked_users

        top_posters = db.session.query(
            User.id, User.username, func.count(Post.id).label('post_count')
        ).join(Post).group_by(User.id).order_by(func.count(Post.id).desc()).limit(5).all()

        return jsonify({
            "posts": {
                "total": total_posts,
                "approved": approved_posts,
                "flagged": flagged_posts,
                "pending": total_posts - approved_posts
            },
            "comments": {
                "total": total_comments,
                "approved": approved_comments,
                "flagged": flagged_comments,
                "pending": total_comments - approved_comments
            },
            "users": {
                "total": total_users,
                "active": active_users,
                "blocked": blocked_users,
                "admins": admin_users
            },
            "top_contributors": [{
                "id": user_id,
                "username": username,
                "post_count": post_count
            } for user_id, username, post_count in top_posters]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch content stats: {str(e)}"}), 500
    bp.route("/stats", methods=["GET"])
@jwt_required()
@admin_required
def get_admin_stats():
   
    try:
        total_users = User.query.count()
        total_posts = Post.query.count()
        total_comments = Comment.query.count()
        
        flagged_posts = Post.query.filter_by(is_flagged=True).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        total_flagged = flagged_posts + flagged_comments
        
        blocked_users = User.query.filter_by(is_blocked=True).count()
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = User.query.filter(User.created_at >= week_ago).count()
        new_posts_week = Post.query.filter(Post.created_at >= week_ago).count()
        new_comments_week = Comment.query.filter(Comment.created_at >= week_ago).count()

        return jsonify({
            "users": total_users,
            "posts": total_posts,
            "comments": total_comments,
            "flagged": total_flagged,
            "flagged_posts": flagged_posts,
            "flagged_comments": flagged_comments,
            "blocked_users": blocked_users,
            "recent_activity": {
                "new_users": new_users_week,
                "new_posts": new_posts_week,
                "new_comments": new_comments_week
            }
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch stats: {str(e)}"}), 500


@admin_bp.route("/flagged/posts", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_posts():
   
    try:
        flagged_posts = Post.query.filter_by(is_flagged=True).order_by(Post.created_at.desc()).all()
        
        return jsonify([{
            "id": p.id,
            "title": p.title,
            "content": p.content[:200] + "..." if len(p.content) > 200 else p.content,
            "user_id": p.user_id,
            "created_at": p.created_at.isoformat(),
            "is_approved": p.is_approved
        } for p in flagged_posts]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch flagged posts: {str(e)}"}), 500


@admin_bp.route("/flagged/comments", methods=["GET"])
@jwt_required()
@admin_required
def get_flagged_comments():
  
    try:
        flagged_comments = Comment.query.filter_by(is_flagged=True).order_by(Comment.created_at.desc()).all()
        
        return jsonify([{
            "id": c.id,
            "content": c.content[:150] + "..." if len(c.content) > 150 else c.content,
            "post_id": c.post_id,
            "user_id": c.user_id,
            "created_at": c.created_at.isoformat(),
            "is_approved": c.is_approved
        } for c in flagged_comments]), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch flagged comments: {str(e)}"}), 500


@admin_bp.route("/activity-trends", methods=["GET"])
@jwt_required()
@admin_required
def get_activity_trends():
   
    try:
        trends_data = {"labels": [], "posts": [], "users": []}
        
        for i in range(6, -1, -1):  
            date = datetime.utcnow() - timedelta(days=i)
            start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = start_of_day + timedelta(days=1)
            
            posts_count = Post.query.filter(
                and_(Post.created_at >= start_of_day, Post.created_at < end_of_day)
            ).count()
            
            users_count = User.query.filter(
                and_(User.created_at >= start_of_day, User.created_at < end_of_day)
            ).count()
            
            trends_data["labels"].append(date.strftime("%m/%d"))
            trends_data["posts"].append(posts_count)
            trends_data["users"].append(users_count)

        return jsonify(trends_data), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch activity trends: {str(e)}"}), 500


@admin_bp.route("/recent-activity", methods=["GET"])
@jwt_required()
@admin_required
def get_recent_activity():
   
    try:
        recent_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
        
        recent_comments = Comment.query.order_by(Comment.created_at.desc()).limit(10).all()
        
        recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

        return jsonify({
            "recent_posts": [{
                "id": p.id,
                "title": p.title,
                "user_id": p.user_id,
                "created_at": p.created_at.isoformat()
            } for p in recent_posts],
            "recent_comments": [{
                "id": c.id,
                "content": c.content[:100] + "..." if len(c.content) > 100 else c.content,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "created_at": c.created_at.isoformat()
            } for c in recent_comments],
            "recent_users": [{
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "created_at": u.created_at.isoformat()
            } for u in recent_users]
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch recent activity: {str(e)}"}), 500


