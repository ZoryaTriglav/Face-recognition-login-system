from flask import Flask, render_template, request, redirect, jsonify
import os
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired

app = Flask(__name__)

# 配置图书管理系统数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'instance', 'books.db')
db = SQLAlchemy(app)


class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    def __repr__(self):
        return f'<Book {self.title}>'


# 配置评论系统数据库连接
app.config['SECRET_KEY'] = '114514'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'instance', 'comments.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db_comments = SQLAlchemy(app)


class Comment(db_comments.Model):
    id = db_comments.Column(db_comments.Integer, primary_key=True)
    name = db_comments.Column(db_comments.String(50), nullable=False)
    content = db_comments.Column(db_comments.Text, nullable=False)


class CommentForm(FlaskForm):
    name = StringField('姓名', validators=[DataRequired()])
    content = TextAreaField('评论', validators=[DataRequired()])
    submit = SubmitField('提交')


db_comments.create_all()
db.create_all()


@app.route('/')
def home():
    books_list = Book.query.limit(6).all()
    form = CommentForm()
    comments = Comment.query.all()
    return render_template('book.html', books=books_list, form=form, comments=comments)


@app.route('/find_book', methods=['POST'])
def find_book():
    book_need_find = request.json.get('bookName')
    book_need_find = Book.query.filter(Book.title.ilike(f'%{book_need_find}%')).all()

    search_results = []
    for book in book_need_find:
        result = {
            'title': book.title,
            'author': book.author,
            'description': book.description
        }
        search_results.append(result)
    print("完成搜索")

    return jsonify(search_results)


@app.route('/submit_book', methods=['POST'])
def add_book():
    book_name = request.json.get('bookName')
    author = request.json.get('author')
    description = request.json.get('description')
    print(f"name:{book_name},au:{author},des:{description}")

    existing_book = Book.query.filter_by(title=book_name, author=author).first()
    if existing_book:
        return jsonify({'message': '图书已存在'})

    new_book = Book(title=book_name, author=author, description=description)
    db.session.add(new_book)
    db.session.commit()
    return jsonify({'message': '保存成功'})


@app.route('/add_comment', methods=['POST'])
def add_comment():
    form = CommentForm()
    if form.validate_on_submit():
        name = form.name.data
        content = form.content.data

        comment = Comment(name=name, content=content)
        db_comments.session.add(comment)
        db_comments.session.commit()

        return redirect('/')
    else:
        return "表单验证失败"


if __name__ == '__main__':
    app.run(debug=True, port=5001)


