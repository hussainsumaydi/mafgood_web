import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from extensions import db
from models.item import Item, ItemCategory, ItemStatus, ItemType, Match
from models.report import Report
from utils.ai_matching import ai_matcher

items_bp = Blueprint('items', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@items_bp.route('/')
def list_items():
    """قائمة كل الأغراض مع فلتر بحث."""
    search    = request.args.get('q', '')
    category  = request.args.get('category', '')
    item_type = request.args.get('type', '')

    query = Item.query.filter_by(status=ItemStatus.ACTIVE)

    if search:
        query = query.filter(Item.item_name.ilike(f'%{search}%'))
    if category:
        try:
            query = query.filter_by(category=ItemCategory(category))
        except ValueError:
            pass
    if item_type:
        try:
            query = query.filter_by(item_type=ItemType(item_type))
        except ValueError:
            pass

    items = query.order_by(Item.created_at.desc()).all()
    categories = [c.value for c in ItemCategory]
    return render_template('items/list.html', items=items,
                           categories=categories, search=search,
                           selected_category=category, selected_type=item_type)


@items_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_item():
    if request.method == 'POST':
        item_name   = request.form.get('item_name', '').strip()
        category    = request.form.get('category', '')
        item_type   = request.form.get('item_type', '')
        location    = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not all([item_name, category, item_type]):
            flash('يرجى ملء جميع الحقول المطلوبة', 'danger')
            return render_template('items/create.html', categories=list(ItemCategory))

        image_path = None
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            save_path  = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            image_path = f'uploads/{filename}'

        try:
            item = Item(
                item_name=item_name,
                category=ItemCategory(category),
                item_type=ItemType(item_type),
                location=location,
                description=description,
                image_path=image_path,
                user_id=current_user.id,
            )
            db.session.add(item)
            db.session.commit()

            # تشغيل المطابقة الذكية تلقائياً إذا كان الغرض مفقوداً
            if item.item_type == ItemType.LOST:
                ai_matcher.run_matching_for_item(item)

            flash('تم نشر الغرض بنجاح!', 'success')
            return redirect(url_for('items.item_detail', item_id=item.id))
        except Exception as e:
            db.session.rollback()
            flash(f'حدث خطأ: {str(e)}', 'danger')

    return render_template('items/create.html', categories=list(ItemCategory))


@items_bp.route('/<int:item_id>')
def item_detail(item_id):
    item = Item.query.get_or_404(item_id)
    matches = []
    if current_user.is_authenticated and item.user_id == current_user.id:
        matches = Match.query.filter_by(source_item_id=item.id)\
                             .order_by(Match.similarity_score.desc()).limit(5).all()
    return render_template('items/detail.html', item=item, matches=matches)


@items_bp.route('/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and not current_user.is_admin:
        flash('غير مصرح لك بتعديل هذا الغرض', 'danger')
        return redirect(url_for('items.item_detail', item_id=item_id))

    if request.method == 'POST':
        item.item_name   = request.form.get('item_name', item.item_name).strip()
        item.location    = request.form.get('location', item.location).strip()
        item.description = request.form.get('description', item.description).strip()
        try:
            item.category  = ItemCategory(request.form.get('category', item.category.value))
        except ValueError:
            pass

        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename   = secure_filename(file.filename)
            save_path  = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            item.image_path = f'uploads/{filename}'

        db.session.commit()
        flash('تم تحديث الغرض بنجاح', 'success')
        return redirect(url_for('items.item_detail', item_id=item_id))

    return render_template('items/edit.html', item=item, categories=list(ItemCategory))


@items_bp.route('/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    if item.user_id != current_user.id and not current_user.is_admin:
        flash('غير مصرح لك بحذف هذا الغرض', 'danger')
        return redirect(url_for('items.item_detail', item_id=item_id))
    item.delete_item()
    flash('تم حذف الغرض', 'info')
    return redirect(url_for('items.list_items'))


@items_bp.route('/<int:item_id>/report', methods=['POST'])
@login_required
def report_item(item_id):
    item   = Item.query.get_or_404(item_id)
    reason = request.form.get('reason', '').strip()
    if not reason:
        flash('يرجى ذكر سبب البلاغ', 'danger')
        return redirect(url_for('items.item_detail', item_id=item_id))
    current_user.submit_report(item_id=item.id, reason=reason)
    flash('تم إرسال البلاغ للمراجعة', 'success')
    return redirect(url_for('items.item_detail', item_id=item_id))


@items_bp.route('/search-by-image', methods=['GET', 'POST'])
@login_required
def search_by_image():
    """بحث بالصورة باستخدام AI."""
    results = []
    if request.method == 'POST':
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename  = secure_filename(file.filename)
            save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'tmp_' + filename)
            file.save(save_path)

            target_vec = ai_matcher.request_img_details(save_path)
            all_items  = Item.query.filter_by(status=ItemStatus.ACTIVE).all()

            for item in all_items:
                if item.image_path:
                    full_path = os.path.join(current_app.root_path, 'static', item.image_path)
                    item_vec  = ai_matcher.request_img_details(full_path)
                    score     = ai_matcher.compare_similarity(target_vec, item_vec)
                    if score >= ai_matcher.threshold:
                        results.append({'item': item, 'score': round(score * 100, 1)})

            results.sort(key=lambda x: x['score'], reverse=True)
            os.remove(save_path)
        else:
            flash('يرجى رفع صورة صالحة', 'danger')

    return render_template('items/search_by_image.html', results=results)
