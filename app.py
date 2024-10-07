from flask import Flask, render_template, url_for, redirect, request, session, abort, flash
from datetime import datetime
from datetime import date
from werkzeug.utils import secure_filename
import os
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_

app = Flask(__name__)
app.app_context().push()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///appdatabase.db"
app.config['SECRET_KEY'] = 'thisisasecretkey'
app.config['UPLOAD_FOLDER'] = 'static/product_images'
app.config['UPLOAD_FOLDER'] = 'static/category_images'
db = SQLAlchemy(app)


class Cart(db.Model):
    cart_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("customer.customer_id"))
    cart_items = db.relationship('CartItem', backref='cart', lazy=True)

class CartItem(db.Model):
    cart_item_id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey("cart.cart_id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.product_id"))
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='cart_items', lazy=True)

class Order(db.Model):
    order_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey("customer.customer_id"))
    sold_date = db.Column(db.Date)
    order_items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    order_item_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.order_id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.product_id"))
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='order_items', lazy=True)

class Category(db.Model):
    category_id = db.Column(db.Integer, primary_key = True)
    category_name = db.Column(db.String, nullable = False)
    image_path = db.Column(db.String, nullable=False)
    products = db.relationship('Product', backref='category', cascade='all, delete-orphan')

class Unit(db.Model):
    unit_id = db.Column(db.Integer, primary_key = True,)
    unit_name = db.Column(db.String, nullable = False)
    products = db.relationship('Product', backref='unit', lazy=True)

class Product(db.Model):
    product_id = db.Column(db.Integer, primary_key = True)
    product_name = db.Column(db.String, nullable = False)
    image_path = db.Column(db.String, nullable=False) 
    manufacture_date = db.Column(db.Date, nullable = False)
    expiry_date = db.Column(db.Date, nullable = False)
    rate_per_unit = db.Column(db.Integer, nullable = False)
    stocks_available = db.Column(db.Integer, nullable = False)
    product_unit = db.Column(db.String, db.ForeignKey("unit.unit_id"))
    product_category_id = db.Column(db.Integer, db.ForeignKey("category.category_id"))

class Customer(db.Model):
    customer_id = db.Column(db.Integer, primary_key = True)
    customer_name = db.Column(db.String(20), nullable = False)
    customer_Username = db.Column(db.String(20), nullable = False, unique=True)
    customer_password = db.Column(db.String(80), nullable = False)
    customer_contact = db.Column(db.String, nullable = False)
    customer_mail = db.Column(db.String, nullable = False)
    customer_country = db.Column(db.String, nullable = False)
    customer_state = db.Column(db.String, nullable = False)
    customer_city = db.Column(db.String, nullable = False)
    customer_pincode = db.Column(db.Integer, nullable = False)
    customer_add = db.Column(db.String, nullable = False)
    customer_landmark = db.Column(db.String, nullable = False)

class Manager(db.Model):
    manager_id = db.Column(db.Integer, primary_key = True)
    manager_name = db.Column(db.String, nullable = False)
    manager_password = db.Column(db.String, nullable = False)
    manager_contact = db.Column(db.String, nullable = False)

def parse_date_string(date_string):
    date_formats = ['%d%m%Y', '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y','%d-%m-%Y']
    for date_format in date_formats:
        try:
            date_obj = datetime.strptime(date_string, date_format).date()
            return date_obj
        except ValueError:
            pass
    raise ValueError("Invalid date format")

@app.route('/')
def index():
    products = Product.query.limit(4).all()
    return render_template('index.html', products=products)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        customer_Username = request.form['customer_Username']
        customer_password = request.form['customer_password']

        user = Customer.query.filter_by(customer_Username=customer_Username).first()
        if user and user.customer_password == customer_password:
            session['user_id'] = user.customer_id
            session['user_name'] = user.customer_name
            return redirect(url_for('dashboard_user'))
        else:
            flash("Invalid credentials. Please try again.")

    return render_template('login.html')

@app.route('/dashboard_user')
def dashboard_user():
    if 'user_id' in session:
        categories = Category.query.all()
        products_query = Product.query.join(Category)
        
        min_price = request.args.get('min_price', type=int)
        max_price = request.args.get('max_price', type=int)
        min_mfg_date = request.args.get('min_mfg_date')
        max_mfg_date = request.args.get('max_mfg_date')
        query = request.args.get('query')
        
        # Filter by query if provided
        if query:
            products_query = products_query.filter(
                or_(
                    Product.product_name.contains(query),
                    Category.category_name.contains(query)
                )
            )
        
        # Filter by price range
        if min_price is not None:
            products_query = products_query.filter(Product.rate_per_unit >= min_price)
        if max_price is not None:
            products_query = products_query.filter(Product.rate_per_unit <= max_price)
        
        # Filter by manufacture date range
        if min_mfg_date:
            if min_mfg_date:
                min_mfg_date_obj = parse_date_string(min_mfg_date)
                products_query = products_query.filter(Product.manufacture_date >= min_mfg_date_obj)
        
        # Retrieve filtered products
        products = products_query.all()
        
        # Organize products by category
        products_by_category = {}
        for category in categories:
            category_products = [product for product in products if product.product_category_id == category.category_id]
            if category_products:
                products_by_category[category] = category_products
        
        # Render the dashboard with filtered data
        return render_template('dashboard_user.html', products_by_category=products_by_category, categories=categories)
    
    else:
        return redirect(url_for('login'))
    
@app.route('/filter', methods=['GET', 'POST'])       
def filter_products():
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    start_date = parse_date_string(request.args.get('start_date'))
    end_date = parse_date_string(request.args.get('end_date'))

    print("Received filters:")
    print("min_price:", min_price)
    print("max_price:", max_price)
    print("start_date:", start_date)
    print("end_date:", end_date)

    filtered_products = Product.query

    if min_price and max_price:
        min_price = int(min_price)
        max_price = int(max_price)
        filtered_products = filtered_products.filter(
            and_(Product.rate_per_unit >= min_price, Product.rate_per_unit <= max_price)
        )
    elif min_price:
        min_price = int(min_price)
        filtered_products = filtered_products.filter(Product.rate_per_unit >= min_price)
    elif max_price:
        max_price = int(max_price)
        filtered_products = filtered_products.filter(Product.rate_per_unit <= max_price)

    if start_date and end_date:
        print("Applying date filter:")
        print("start_date:", start_date)
        print("end_date:", end_date)

        filtered_products = filtered_products.filter(
            and_(Product.manufacture_date >= start_date, Product.manufacture_date <= end_date)
        )
        
    print("Filtered products count:", filtered_products.count())

    return render_template('dashboard_user.html', products=filtered_products.all())


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        customer_Username = request.form['customer_Username']
        customer_password = request.form['customer_password']
        customer_contact = request.form['customer_contact']
        customer_mail = request.form['customer_mail']
        customer_country = request.form['customer_country']
        customer_state = request.form['customer_state']
        customer_city = request.form['customer_city']
        customer_pincode = request.form['customer_pincode']
        customer_add = request.form['customer_add']
        customer_landmark = request.form['customer_landmark']

        existing_user = Customer.query.filter_by(customer_Username=customer_Username).first()
        if existing_user:
            return "Username already taken. Please choose a different one."

        new_customer = Customer(
            customer_name=customer_name,
            customer_Username=customer_Username,
            customer_password=customer_password,
            customer_contact=customer_contact,
            customer_mail=customer_mail,
            customer_country=customer_country,
            customer_state=customer_state,
            customer_city=customer_city,
            customer_pincode=customer_pincode,
            customer_add=customer_add,
            customer_landmark=customer_landmark
        )

        db.session.add(new_customer)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('new_user.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        manager_name = request.form['manager_name']
        manager_password = request.form['manager_password']

        manager = Manager.query.filter_by(manager_name=manager_name).first()
        if manager and manager.manager_password == manager_password:
            session['admin_id'] = manager.manager_id
            session['admin_name'] = manager.manager_name
            return redirect(url_for('dashboard_admin'))
        else:
            flash("Invalid credentials. Please try again.")

    return render_template('admin_login.html')

@app.route('/dashboard_admin')
def dashboard_admin():
    if 'admin_id' in session:
        products = Product.query.limit(4).all()
        orders = Order.query.order_by(Order.order_id.desc()).limit(4).all()
        return render_template('dashboard_admin.html', products=products, orders=orders)
    else:
        return redirect(url_for('admin_login'))    

@app.route('/products')
def get_products():
    if 'admin_id' in session:
        products = Product.query.all()
        return render_template('products.html', products=products)
    else:
        return redirect(url_for('admin_login'))

@app.route('/products/add', methods=['GET', 'POST'])
def add_product():
    if 'admin_id' in session:
        if request.method == 'POST':
            product_name = request.form['product_name']
            manufacture_date = parse_date_string(request.form['manufacture_date'])
            expiry_date = parse_date_string(request.form['expiry_date'])
            rate_per_unit = request.form['rate_per_unit']
            stocks_available = request.form['stocks_available']
            product_unit = request.form['product_unit']
            product_category = request.form['product_category']

            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = f"product_images/{filename}"
                else:
                    image_path = '/static/images/default_product_image.png'
            else:
                image_path = '/static/images/default_product_image.png'

            new_product = Product(
                product_name=product_name,
                manufacture_date=manufacture_date,
                expiry_date=expiry_date,
                image_path=image_path,
                rate_per_unit=rate_per_unit,
                stocks_available=stocks_available,
                product_unit=product_unit,
                product_category_id=product_category
            )

            db.session.add(new_product)
            db.session.commit()

            return redirect(url_for('get_products'))

        return render_template('add_product.html', categories=Category.query.all(), units=Unit.query.all())
    else:
        return redirect(url_for('admin_login'))

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'admin_id' in session:
        product = Product.query.get(product_id)

        if request.method == 'POST':
            product.product_name = request.form['product_name']
            product.manufacture_date = parse_date_string(request.form['manufacture_date'])
            product.expiry_date = parse_date_string(request.form['expiry_date'])
            product.rate_per_unit = request.form['rate_per_unit']
            product.stocks_available = request.form['stocks_available']
            product.product_unit = request.form['product_unit']
            product.product_category = request.form['product_category']

            if 'image' in request.files:
                image = request.files['image']
                if image.filename != '':
                    filename = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    product.image_path = f"product_images/{filename}"

            db.session.commit()

            return redirect(url_for('get_products'))

        return render_template('edit_product.html', product=product, categories=Category.query.all(), units=Unit.query.all())
    else:
        return redirect(url_for('admin_login'))

@app.route('/products/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'admin_id' in session:
        product = Product.query.get(product_id)
        db.session.delete(product)
        db.session.commit()
        return redirect(url_for('get_products'))
    else:
        return redirect(url_for('admin_login'))

@app.route('/customers')
def get_customers():
    if 'admin_id' in session:
        customers = Customer.query.all()
        return render_template('customers.html', customers=customers)
    else:
        return redirect(url_for('admin_login'))

# @app.route('/carts')
# def get_carts():
#     carts = Cart.query.all()
#     return render_template('user_cart.html', carts=carts)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = request.form['product_id']
    quantity = request.form['quantity']

    if 'user_id' in session:
        user_id = session['user_id']

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)

        cart_item = CartItem.query.filter_by(cart_id=cart.cart_id, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += int(quantity)
        else:
            cart_item = CartItem(cart_id=cart.cart_id, product_id=product_id, quantity=int(quantity))
            db.session.add(cart_item)

        db.session.commit()

        return redirect(url_for('dashboard_user'))
    else:
        return redirect(url_for('login'))

@app.route('/update_cart_item/<int:cart_item_id>', methods=['POST'])
def update_cart_item(cart_item_id):
    if 'user_id' in session:

        quantity = int(request.form['quantity'])

        cart_item = CartItem.query.get(cart_item_id)
        if not cart_item:
            abort(404)

        cart_item.quantity = quantity
        db.session.commit()

        return redirect(url_for('view_cart'))
    
    else:
        return redirect(url_for('login'))

@app.route('/delete_cart_item/<int:cart_item_id>')
def delete_cart_item(cart_item_id):
    if 'user_id' in session:
        cart_item = CartItem.query.get(cart_item_id)
        if not cart_item:
            abort(404)

        db.session.delete(cart_item)
        db.session.commit()

        return redirect(url_for('view_cart'))
    else:
        return redirect(url_for('login'))

@app.route('/user_cart')
def view_cart():
    if 'user_id' in session:
        user_id = session['user_id']

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()

        total_price = 0
        for item in cart.cart_items:
            total_price += item.product.rate_per_unit * item.quantity

        return render_template('user_cart.html', cart=cart, total_price=total_price)
    else:
        return redirect(url_for('login'))

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' in session:
        user_id = session['user_id']

        cart = Cart.query.filter_by(user_id=user_id).first()
        if not cart:
            cart = Cart(user_id=user_id)
            db.session.add(cart)
            db.session.commit()

        elif not cart.cart_items:
            flash("Your cart is empty. Please add items to your cart before placing an order.", "danger")
            return redirect(url_for('view_cart'))

        today = date.today()
        order = Order(user_id=user_id, sold_date=today)
        db.session.add(order)
        db.session.commit()

        for item in cart.cart_items:
            order_item = OrderItem(order_id=order.order_id, product_id=item.product_id, quantity=item.quantity)
            db.session.add(order_item)

            product = Product.query.get(item.product_id)
            if product.stocks_available >= item.quantity:
                product.stocks_available -= item.quantity
            else:
                db.session.rollback()
                return "Not enough stock available for some products in your cart. Please review your order and try again."

        for item in cart.cart_items:
            db.session.delete(item)

        db.session.commit()

        return redirect(url_for('order_confirmation', order_id=order.order_id))
    else:
        return redirect(url_for('login'))

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' in session:
        order = Order.query.get(order_id)
        if not order:
            abort(404)

        total_price = 0
        for item in order.order_items:
            total_price += item.product.rate_per_unit * item.quantity

        return render_template('order_customer.html', order=order, total_price=total_price)
    else:
        return redirect(url_for('login'))

@app.route('/user_orders')
def view_orders():
    if 'user_id' in session:
        user_id = session['user_id']

        orders = Order.query.filter_by(user_id=user_id).order_by(Order.order_id.desc()).all()

        def calculate_total_price(order):
            total_price = sum(
                item.product.rate_per_unit * item.quantity 
                for item in order.order_items 
                if item.product is not None
            )
            return total_price
        
        return render_template('user_orders.html', orders=orders, calculate_total_price=calculate_total_price)

    else:
        return redirect(url_for('login'))

@app.route('/orders')
def get_orders():
    if 'admin_id' in session:
        orders = Order.query.order_by(Order.order_id.desc()).all()
        return render_template('orders.html', orders=orders)
    else:
        return redirect(url_for('admin_login'))

@app.route('/managers')
def get_managers():
    if 'admin_id' in session:
        managers = Manager.query.all()
        return render_template('managers.html', managers=managers)
    else:
        return redirect(url_for('admin_login'))

@app.route('/categories')
def get_categories():
    if 'admin_id' in session:
        categories = Category.query.all()
        return render_template('categories.html', categories=categories)
    else:
        return redirect(url_for('admin_login'))

@app.route('/categories/add', methods=['GET', 'POST'])
def add_category():
    if 'admin_id' in session:
        if request.method == 'POST':
            category_name = request.form['category_name']
            image = request.files['image']

            if image:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f'category_images/{filename}'
            else:
                image_path = '/static/images/default_category_image.png'

            new_category = Category(
                category_name=category_name,
                image_path=image_path
            )

            db.session.add(new_category)
            db.session.commit()

            return redirect(url_for('get_categories'))

        return render_template('add_category.html')
    else:
        return redirect(url_for('admin_login'))

@app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
def edit_category(category_id):
    if 'admin_id' in session:
        category = Category.query.get(category_id)

        if request.method == 'POST':
            category_name = request.form['category_name']
            image = request.files['image']

            if image:
                filename = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f'category_images/{filename}'
            else:
                image_path = category.image_path

            category.category_name = category_name
            category.image_path = image_path
            db.session.commit()

            return redirect(url_for('get_categories'))

        return render_template('edit_category.html', category=category)
    else:
        return redirect(url_for('admin_login'))

@app.route('/categories/delete/<int:category_id>')
def delete_category(category_id):
    if 'admin_id' in session:
        category = Category.query.get(category_id)

        if category is None:
            return redirect(url_for('get_categories'))

        if category.image_path:
            image_path = category.image_path.lstrip('/')
            full_image_path = os.path.join(app.root_path, image_path)
            if os.path.exists(full_image_path):
                os.remove(full_image_path)

        db.session.delete(category)
        db.session.commit()

        return redirect(url_for('get_categories'))
    else:
        return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)