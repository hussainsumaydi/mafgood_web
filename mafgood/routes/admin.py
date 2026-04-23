from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from extensions import db
from models.user import User
from models.item import Item, ItemStatus
from models.report import Report

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('هذه الصفحة للمسؤولين فقط', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    stats = {
        'total_users':   User.query.count(),
        'total_items':   Item.query.count(),
        'active_items':  Item.query.filter_by(status=ItemStatus.ACTIVE).count(),
        'pending_reports': Report.query.filter_by(status='pending').count(),
    }
    recent_reports = Report.query.filter_by(status='pending')\
                                 .order_by(Report.created_at.desc()).limit(10).all()
    return render_template('admin/dashboard.html', stats=stats, reports=recent_reports)


@admin_bp.route('/reports')
@login_required
@admin_required
def view_reports():
    reports = Report.query.order_by(Report.created_at.desc()).all()
    return render_template('admin/reports.html', reports=reports)


@admin_bp.route('/reports/<int:report_id>/update', methods=['POST'])
@login_required
@admin_required
def update_report_status(report_id):
    report = Report.query.get_or_404(report_id)
    new_status = request.form.get('status', 'reviewed')
    report.status = new_status
    db.session.commit()
    flash('تم تحديث حالة البلاغ', 'success')
    return redirect(url_for('admin.view_reports'))


@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@login_required
@admin_required
def block_profile(user_id):
    user = User.query.get_or_404(user_id)
    user.profile_status = 'blocked'
    db.session.commit()
    flash(f'تم حظر المستخدم {user.username}', 'warning')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/suspend', methods=['POST'])
@login_required
@admin_required
def suspend_account(user_id):
    user = User.query.get_or_404(user_id)
    user.profile_status = 'suspended'
    db.session.commit()
    flash(f'تم تعليق حساب {user.username}', 'warning')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_account(user_id):
    user = User.query.get_or_404(user_id)
    user.profile_status = 'active'
    db.session.commit()
    flash(f'تم تفعيل حساب {user.username}', 'success')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_account(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('تم حذف الحساب', 'info')
    return redirect(url_for('admin.manage_users'))


@admin_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_post(item_id):
    item = Item.query.get_or_404(item_id)
    item.delete_item()
    flash('تم حذف المنشور', 'info')
    return redirect(url_for('admin.dashboard'))
