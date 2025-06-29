from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from models import db, Comment, User, Post, Like
from datetime import datetime, timezone
import traceback
import logging


try:
    from .utils import block_check_required
except ImportError:
    def block_check_required(f):
       
        def wrapper(*args, **kwargs):
            try:
                current_user_id = get_jwt_identity()
                current_user = User.query.get(current_user_id)
                if current_user and current_user.is_blocked:
                    return jsonify({"error": "User is blocked"}), 403
                return f(*args, **kwargs)
            except Exception as e:
                return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper

logger = logging.getLogger(__name__)

comment_bp = Blueprint('comments', __name__)

def serialize_comment_with_stats(comment, current_user_id=None, include_admin_info=False):
   
    try:
      
        likes_count = Like.query.filter_by(comment_id=comment.id).count()
        liked_by_user = False
        if current_user_id:
            liked_by_user = (
                Like.query.filter_by(comment_id=comment.id, user_id=current_user_id).first()
                is not None
            )
        
       
        author = User.query.get(comment.user_id)
        
       
        data = {
            'id': comment.id,
            'content': comment.content,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'parent_id': comment.parent_id,
            'author': {
                'id': author.id,
                'username': author.username,
                'avatar_url': getattr(author, 'avatar_url', None)
            } if author else {"id": None, "username": "Unknown"},
            'username': author.username if author else "Unknown",
            'created_at': comment.created_at.isoformat() if comment.created_at else None,
            'updated_at': comment.updated_at.isoformat() if hasattr(comment, 'updated_at') and comment.updated_at else None,
            'is_approved': getattr(comment, 'is_approved', True),
            'is_flagged': getattr(comment, 'is_flagged', False),
            'likes_count': likes_count,
            'liked_by_user': liked_by_user,
            'replies_count': Comment.query.filter_by(parent_id=comment.id, is_approved=True).count(),
        }
        
     
        if hasattr(comment, 'approved_at'):
            data['approved_at'] = comment.approved_at.isoformat() if comment.approved_at else None
        
        if hasattr(comment, 'requires_reapproval'):
            data['requires_reapproval'] = comment.requires_reapproval()
        else:
            data['requires_reapproval'] = False
            
        if hasattr(comment, 'has_content_changed'):
            data['has_content_changed'] = comment.has_content_changed()
        else:
            data['has_content_changed'] = False
        
       
        if include_admin_info and hasattr(comment, 'approved_by') and comment.approved_by:
            approver = User.query.get(comment.approved_by)
            if approver:
                data['approved_by'] = {
                    'id': approver.id,
                    'username': approver.username
                }
            if hasattr(comment, 'original_content'):
                data['original_content'] = comment.original_content
        
        return data
        
    except Exception as e:
        logger.error(f"Error serializing comment {comment.id}: {e}")
       
        author = User.query.get(comment.user_id)
        return {
            'id': comment.id,
            'content': comment.content,
            'post_id': comment.post_id,
            'user_id': comment.user_id,
            'parent_id': comment.parent_id,
            'author': {
                'id': author.id,
                'username': author.username
            } if author else {"id": None, "username": "Unknown"},
            'username': author.username if author else "Unknown",
            'created_at': comment.created_at.isoformat() if comment.created_at else None,
            'is_approved': getattr(comment, 'is_approved', True),
            'is_flagged': getattr(comment, 'is_flagged', False),
            'likes_count': 0,
            'liked_by_user': False,
            'requires_reapproval': False,
            'has_content_changed': False
        }

@comment_bp.route("/posts/<int:post_id>/comments", methods=["GET"])
def get_post_comments(post_id):
    """Get comments for a specific post - Hide disapproved comments from general users"""
    try:
      
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

      
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

       
        query = Comment.query.filter_by(post_id=post_id)
        
     
        if current_user and current_user.is_admin:
         
            pass
        else:
         
            if current_user_id:
                query = query.filter(
                    db.or_(
                        Comment.is_approved == True,
                        Comment.user_id == current_user_id
                    )
                )
            else:
             
                query = query.filter(Comment.is_approved == True)
        
      
        comments = query.order_by(Comment.created_at.asc()).all()
        
        
        include_admin_info = current_user and current_user.is_admin
        comments_data = [
            serialize_comment_with_stats(c, current_user_id, include_admin_info) 
            for c in comments
        ]
        
        return jsonify(comments_data), 200

    except Exception as e:
        logger.error(f"Error fetching comments for post {post_id}: {e}")
        return jsonify({"error": "Failed to fetch comments", "message": str(e)}), 500

@comment_bp.route("/posts/<int:post_id>/comments", methods=["POST"])
@jwt_required()
@block_check_required
def create_post_comment(post_id):
  
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404

       
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

        content = data.get("content", "").strip()
        parent_id = data.get("parent_id")

        if not content:
            return jsonify({"error": "Comment content is required"}), 400

        if len(content) > 1000:
            return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400

      
        if parent_id:
            try:
                parent_id = int(parent_id)
                parent_comment = Comment.query.get(parent_id)
                if not parent_comment or parent_comment.post_id != post_id:
                    return jsonify({"error": "Invalid parent comment"}), 400
              
                if not parent_comment.is_approved and not current_user.is_admin:
                    return jsonify({"error": "Cannot reply to unapproved comment"}), 400
            except ValueError:
                return jsonify({"error": "Invalid parent_id format"}), 400

       
        is_approved = current_user.is_admin

     
        comment = Comment(
            content=content,
            post_id=post_id,
            user_id=current_user_id,
            parent_id=parent_id,
            created_at=datetime.now(timezone.utc),
            is_approved=is_approved,
            is_flagged=False
        )

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)

   
        if is_approved and hasattr(comment, 'approve'):
            comment.approve(current_user)

        db.session.add(comment)
        db.session.commit()

      
        include_admin_info = current_user.is_admin
        comment_data = serialize_comment_with_stats(comment, current_user_id, include_admin_info)
        
        if not is_approved:
            comment_data['message'] = 'Comment posted successfully and is pending admin approval'
        else:
            comment_data['message'] = 'Comment posted and approved automatically'

        return jsonify(comment_data), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating comment: {e}")
        return jsonify({"error": "Failed to create comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["GET"])
def get_comment(comment_id):
 
    try:
    
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

     
        can_view = (
            getattr(comment, 'is_approved', True) or 
            (current_user and current_user.is_admin) or  
            (current_user_id == comment.user_id)  
        )

        if not can_view:
            return jsonify({"error": "Comment not found"}), 404

        include_admin_info = current_user and current_user.is_admin
        comment_data = serialize_comment_with_stats(comment, current_user_id, include_admin_info)
        return jsonify(comment_data), 200

    except Exception as e:
        logger.error(f"Error fetching comment {comment_id}: {e}")
        return jsonify({"error": "Failed to fetch comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["PATCH"])
@jwt_required()
@block_check_required
def update_comment(comment_id):
   
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        comment = Comment.query.get(comment_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        if comment.user_id != current_user_id and not current_user.is_admin:
            return jsonify({"error": "Permission denied"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON body provided"}), 400

      
        content_changed = False
        requires_reapproval = False
        message = "Comment updated successfully"

       
        if 'content' in data:
            new_content = data['content'].strip()
            if not new_content: 
                return jsonify({"error": "Content cannot be empty"}), 400
            if len(new_content) > 1000:
                return jsonify({"error": "Comment content too long (max 1000 characters)"}), 400
            
            if comment.content != new_content:
                content_changed = True
                old_content = comment.content
                comment.content = new_content
                
               
                if not current_user.is_admin and comment.user_id == current_user_id:
                    if hasattr(comment, 'requires_reapproval'):
                        requires_reapproval = comment.requires_reapproval()
                    elif getattr(comment, 'is_approved', True):
                     
                        requires_reapproval = True

        if current_user.is_admin:
            if 'is_approved' in data: 
                new_approval_state = bool(data['is_approved'])
                
                if new_approval_state:
                   
                    can_approve = (
                        not getattr(comment, 'is_approved', True) or  
                        content_changed or  
                        (hasattr(comment, 'has_content_changed') and comment.has_content_changed()) or  
                        not hasattr(comment, 'approved_at') or comment.approved_at is None  
                    )
                    
                    if can_approve:
                        if hasattr(comment, 'approve'):
                            comment.approve(current_user)
                        else:
                            comment.is_approved = True
                            comment.approved_by = current_user_id
                            comment.approved_at = datetime.now(timezone.utc)
                        requires_reapproval = False
                        message = "Comment approved successfully"
                    else:
                        return jsonify({
                            "error": "Comment cannot be approved - no changes detected since last approval"
                        }), 400
                else:
                  
                    if hasattr(comment, 'disapprove'):
                        comment.disapprove()
                    else:
                        comment.is_approved = False
                    message = "Comment disapproved successfully"
                        
            if 'is_flagged' in data: 
                comment.is_flagged = bool(data['is_flagged'])
                flag_action = "flagged" if comment.is_flagged else "unflagged"
                message = f"Comment {flag_action} successfully"
        else:
           
            if requires_reapproval:
                comment.is_approved = False
                comment.approved_by = None
                comment.approved_at = None
                message = "Comment updated successfully and is pending admin approval due to content changes"

       
        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        include_admin_info = current_user.is_admin
        comment_data = serialize_comment_with_stats(comment, current_user_id, include_admin_info)
        comment_data['message'] = message

        return jsonify(comment_data), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating comment {comment_id}: {e}")
        return jsonify({"error": "Failed to update comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@jwt_required()
@block_check_required
def delete_comment(comment_id):
  
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        comment = Comment.query.get(comment_id)
        
        if not current_user:
            return jsonify({"error": "User not found"}), 404
        if not comment:
            return jsonify({"error": "Comment not found"}), 404
        if comment.user_id != current_user_id and not current_user.is_admin:
            return jsonify({"error": "Permission denied"}), 403

      
        Like.query.filter_by(comment_id=comment_id).delete()
        
      
        Comment.query.filter_by(parent_id=comment_id).delete()
        
        db.session.delete(comment)
        db.session.commit()
        
        return jsonify({"message": "Comment deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting comment {comment_id}: {e}")
        return jsonify({"error": "Failed to delete comment", "message": str(e)}), 500

@comment_bp.route("/comments/<int:comment_id>/like", methods=["POST"])
@jwt_required()
@block_check_required
def toggle_comment_like(comment_id):
 
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        comment = Comment.query.get(comment_id)
        
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

      
        can_interact = (
            getattr(comment, 'is_approved', True) or  
            (current_user and current_user.is_admin) or  
            (current_user_id == comment.user_id)  
        )

        if not can_interact:
            return jsonify({"error": "Cannot interact with this comment"}), 403

        existing = Like.query.filter_by(comment_id=comment_id, user_id=current_user_id).first()
        if existing:
            db.session.delete(existing)
            message = "Comment unliked"
            liked = False
        else:
            new_like = Like(
                comment_id=comment_id,
                user_id=current_user_id,
                created_at=datetime.now(timezone.utc)
            )
            db.session.add(new_like)
            message = "Comment liked"
            liked = True

        db.session.commit()
        
        likes_count = Like.query.filter_by(comment_id=comment_id).count()
        return jsonify({
            "message": message,
            "likes": likes_count,
            "likes_count": likes_count,
            "liked_by_user": liked
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error toggling like on comment {comment_id}: {e}")
        return jsonify({"error": "Failed to toggle like", "message": str(e)}), 500


@comment_bp.route("/comments", methods=["GET"])
def list_comments():
    
    try:
    
        current_user_id = None
        current_user = None
        try:
            verify_jwt_in_request(optional=True)
            current_user_id = get_jwt_identity()
            if current_user_id:
                current_user = User.query.get(current_user_id)
        except:
            pass

       
        post_id = request.args.get("post_id", type=int)
        user_id = request.args.get("user_id", type=int)
        all_comments = request.args.get("all", "").lower() == "true"
        admin_mode = request.args.get("admin", "").lower() == "true"
        pending_only = request.args.get("pending", "").lower() == "true"
        flagged_only = request.args.get("flagged", "").lower() == "true"
        limit = min(request.args.get("limit", 100, type=int), 500)

      
        query = Comment.query

      
        if post_id:
            query = query.filter_by(post_id=post_id)
        if user_id:
            query = query.filter_by(user_id=user_id)

    
        if pending_only:
            query = query.filter(Comment.is_approved == False)
        elif flagged_only:
            query = query.filter(Comment.is_flagged == True)
        elif not (current_user and current_user.is_admin and (all_comments or admin_mode)):
           
            if current_user_id:
                query = query.filter(
                    db.or_(
                        Comment.is_approved == True,
                        Comment.user_id == current_user_id
                    )
                )
            else:
                query = query.filter(Comment.is_approved == True)

    
        comments = query.order_by(Comment.created_at.desc()).limit(limit).all()
        
      
        include_admin_info = current_user and current_user.is_admin
        comments_data = [
            serialize_comment_with_stats(c, current_user_id, include_admin_info) 
            for c in comments
        ]
        
        return jsonify(comments_data), 200

    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        return jsonify({"error": "Failed to fetch comments", "message": str(e)}), 500


@comment_bp.route("/admin/comments/<int:comment_id>/approve", methods=["PATCH"])
@jwt_required()
def admin_approve_comment(comment_id):
   
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json() or {}
        is_approved = bool(data.get('is_approved', True))
        
        if is_approved:
            
            can_approve = (
                not getattr(comment, 'is_approved', True) or  
                (hasattr(comment, 'has_content_changed') and comment.has_content_changed()) or  
                not hasattr(comment, 'approved_at') or comment.approved_at is None  
            )
            
            if not can_approve:
                return jsonify({
                    "error": "Comment cannot be approved - no changes detected since last approval"
                }), 400
            
            
            if hasattr(comment, 'approve'):
                comment.approve(current_user)
            else:
                comment.is_approved = True
                comment.approved_by = current_user_id
                comment.approved_at = datetime.now(timezone.utc)
        else:
           
            if hasattr(comment, 'disapprove'):
                comment.disapprove()
            else:
                comment.is_approved = False

        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()

        action = 'approved' if is_approved else 'rejected'
        include_admin_info = True
        return jsonify({
            "message": f"Comment {action} successfully",
            "comment": serialize_comment_with_stats(comment, current_user_id, include_admin_info)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error approving comment {comment_id}: {e}")
        return jsonify({"error": "Failed to update approval", "message": str(e)}), 500

@comment_bp.route("/admin/comments/<int:comment_id>/flag", methods=["PATCH"])
@jwt_required()
def admin_flag_comment(comment_id):
   
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        comment = Comment.query.get(comment_id)
        if not comment:
            return jsonify({"error": "Comment not found"}), 404

        data = request.get_json() or {}
        is_flagged = bool(data.get('is_flagged', True))

        comment.is_flagged = is_flagged
        if hasattr(comment, 'updated_at'):
            comment.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        action = 'flagged' if is_flagged else 'unflagged'
        include_admin_info = True
        return jsonify({
            "message": f"Comment {action} successfully",
            "comment": serialize_comment_with_stats(comment, current_user_id, include_admin_info)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error flagging comment {comment_id}: {e}")
        return jsonify({"error": "Failed to flag comment", "message": str(e)}), 500

@comment_bp.route("/admin/comments/pending", methods=["GET"])
@jwt_required()
def get_pending_comments():
 
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

     
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        
        pending_query = Comment.query.filter_by(is_approved=False)\
                                    .order_by(Comment.created_at.desc())
        
     
        if request.args.get('paginate', 'false').lower() == 'true':
            pagination = pending_query.paginate(
                page=page, per_page=per_page, error_out=False
            )
            pending_comments = pagination.items
        else:
            pending_comments = pending_query.all()
        
        include_admin_info = True
        comments_data = [
            serialize_comment_with_stats(c, current_user_id, include_admin_info) 
            for c in pending_comments
        ]
        
        response_data = {
            "pending_comments": comments_data,
            "count": len(comments_data)
        }
        
     
        if request.args.get('paginate', 'false').lower() == 'true':
            response_data["pagination"] = {
                "page": page,
                "per_page": per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_prev": pagination.has_prev,
                "has_next": pagination.has_next
            }
        
        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error fetching pending comments: {e}")
        return jsonify({"error": "Failed to fetch pending comments", "message": str(e)}), 500

@comment_bp.route("/admin/comments/flagged", methods=["GET"])
@jwt_required()
def get_flagged_comments():
   
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

     
        flagged_comments = Comment.query.filter_by(is_flagged=True)\
                                       .order_by(Comment.created_at.desc())\
                                       .all()
        
        include_admin_info = True
        comments_data = [
            serialize_comment_with_stats(c, current_user_id, include_admin_info) 
            for c in flagged_comments
        ]
        
        return jsonify({
            "flagged_comments": comments_data,
            "count": len(comments_data)
        }), 200

    except Exception as e:
        logger.error(f"Error fetching flagged comments: {e}")
        return jsonify({"error": "Failed to fetch flagged comments", "message": str(e)}), 500

@comment_bp.route("/admin/comments/stats", methods=["GET"])
@jwt_required()
def get_comment_stats():
   
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        if not current_user or not current_user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

      
        total_comments = Comment.query.count()
        approved_comments = Comment.query.filter_by(is_approved=True).count()
        pending_comments = Comment.query.filter_by(is_approved=False).count()
        flagged_comments = Comment.query.filter_by(is_flagged=True).count()
        
       
        return jsonify({
            "total_comments": total_comments,
            "approved_comments": approved_comments,
            "pending_comments": pending_comments,
            "flagged_comments": flagged_comments,
            "approval_rate": round((approved_comments / total_comments * 100) if total_comments > 0 else 0, 1),
            "features": {
                "approval_system": True,
                "change_tracking": True,
                "flagging_system": True,
                "voting_system": False  
            }
        }), 200

    except Exception as e:
        logger.error(f"Error fetching comment stats: {e}")
        return jsonify({"error": "Failed to fetch comment statistics", "message": str(e)}), 500


def test_comments():
    """Test endpoint to verify comments system is working"""
    try:
        comment_count = Comment.query.count()
        
       
        approved_count = 0
        flagged_count = 0
        pending_count = 0
        
        if hasattr(Comment, 'is_approved'):
            approved_count = Comment.query.filter_by(is_approved=True).count()
            pending_count = Comment.query.filter_by(is_approved=False).count()
        if hasattr(Comment, 'is_flagged'):
            flagged_count = Comment.query.filter_by(is_flagged=True).count()
        
        return jsonify({
            "success": True,
            "message": "Comments system is working (NO VOTING - Enhanced Approval System)",
            "total_comments": comment_count,
            "approved_comments": approved_count,
            "pending_comments": pending_count,
            "flagged_comments": flagged_count,
            "features": {
                "approval_system": hasattr(Comment, 'is_approved'),
                "change_tracking": hasattr(Comment, 'content_hash'),
                "flagging_system": hasattr(Comment, 'is_flagged'),
                "voting_system": False, 
                "like_system": True,
                "reply_system": True,
                "admin_controls": True
            },
            "endpoints": {
                "get_post_comments": "GET /api/posts/<id>/comments",
                "create_comment": "POST /api/posts/<id>/comments",
                "get_comment": "GET /api/comments/<id>",
                "update_comment": "PATCH /api/comments/<id>",
                "delete_comment": "DELETE /api/comments/<id>",
                "like_comment": "POST /api/comments/<id>/like",
                "list_comments": "GET /api/comments",
                "admin_approve": "PATCH /api/admin/comments/<id>/approve",
                "admin_flag": "PATCH /api/admin/comments/<id>/flag",
                "get_pending": "GET /api/admin/comments/pending",
                "get_flagged": "GET /api/admin/comments/flagged",
                "comment_stats": "GET /api/admin/comments/stats"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({"error": f"Test failed: {str(e)}"}), 500