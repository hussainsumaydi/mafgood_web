from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models.item import Item
from models.report import Notification

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/')
@login_required
def my_profile():
    my_items = Item.query.filter_by(user_id=current_user.id)\
                         .order_by(Item.created_at.desc()).all()
    return render_template('profile/profile.html', user=current_user, items=my_items)


@profile_bp.route('/notifications')
@login_required
def notifications():
    from models.report import Notification
    notifications = Notification.query.filter_by(user_id=current_user.id)\
                                .order_by(Notification.created_at.desc()).all()
    return render_template('profile/notifications.html', notifications=notifications)


@profile_bp.route('/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        full_name        = request.form.get('full_name', '').strip()
        phone_number     = request.form.get('phone_number', '').strip()
        university_email = request.form.get('university_email', '').strip()

        success = current_user.update_profile_info(
            full_name=full_name,
            phone_number=phone_number or None,
            university_email=university_email or None,
        )
        if success:
            flash('تم تحديث الملف الشخصي بنجاح', 'success')
        else:
            flash('حدث خطأ أثناء التحديث', 'danger')
        return redirect(url_for('profile.my_profile'))

    return render_template('profile/edit.html', user=current_user)


@profile_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_user.check_password(current_password):
            flash('كلمة المرور الحالية غير صحيحة', 'danger')
            return render_template('profile/change_password.html')

        if new_password != confirm_password:
            flash('كلمتا المرور الجديدتان غير متطابقتين', 'danger')
            return render_template('profile/change_password.html')

        if len(new_password) < 6:
            flash('يجب أن تكون كلمة المرور 6 أحرف على الأقل', 'danger')
            return render_template('profile/change_password.html')

        current_user.reset_password(new_password)
        flash('تم تغيير كلمة المرور بنجاح', 'success')
        return redirect(url_for('profile.my_profile'))

    return render_template('profile/change_password.html')


@profile_bp.route('/user/<int:user_id>')
def view_user_profile(user_id):
    from models.user import User
    user  = User.query.get_or_404(user_id)
    from models.item import ItemStatus
    items = Item.query.filter_by(user_id=user_id, status=ItemStatus.NOT_FOUND)\
                      .order_by(Item.created_at.desc()).all()
    return render_template('profile/view_user.html', user=user, items=items)
