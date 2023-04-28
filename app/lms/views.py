from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import or_

from sqlalchemy.exc import OperationalError
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user, current_user
from app import bcrypt, db
from app.auth.forms import LoginForm, RegisterForm, UpdateForm
from app.auth.models import User, Book, BookIssuanceTracker, BookIssuanceHistory
from app import login_manager  # the variable from Flask-login
from app.lms.forms import AddBookForm, IssueBookForm, RenewBookForm, SearchBookForm

lms_bp = Blueprint("lms", __name__)


## fixing issue with key -- userid instead of id
@login_manager.user_loader
def load_user(userid):
    return User.query.get(int(userid))


@lms_bp.route("/addbook", methods=["GET", "POST"])
@login_required
def addbook():
    if request.method == 'GET':
        form = AddBookForm(request.form)

        return render_template("lms/addbook.html", form=form)


    if request.method == 'POST':

        form = AddBookForm(request.form)
        if form.validate:
            totalnoofcopies = form.totalnoofcopies.data
            book = Book(title=form.title.data, authors=form.authors.data, publisher=form.publisher.data,
                        edition=form.edition.data, shelfnum=form.shelfnum.data,
                        isbn=form.isbn.data, description=form.description.data, totalnoofcopies=form.totalnoofcopies.data,
                        availablenoofcopies=form.totalnoofcopies.data)

            try:

                for _ in range(totalnoofcopies):
                    booksforissuance = BookIssuanceTracker()
                    book.issuance.append(booksforissuance)
                    db.session.add(book)
                    db.session.commit()


            except:
                flash("Unable to commit", "success")

            print(form.errors)
            print(form)

            flash("Book entry added", "success")

            return render_template("lms/addbook.html", form=form)

        return render_template("lms/addbook.html", form=form)


@lms_bp.route("/issuebook", methods=["GET", "POST"])
@login_required
def issuebook():
    if request.method == 'GET':
        form = IssueBookForm(request.form)
        # list the books
        books = Book.query.filter(Book.availablenoofcopies > 0).all()
        users = User.query.filter_by().all()
        if books:
            return render_template("lms/issuebook.html", books=Book.query.all(), users=users, form=form)
        flash("Books Available  for issue: 0")
        users = User.query.all()
        return render_template(
            "lms/issuebook.html", books=Book.query.all(), users=users, form=form)

    if request.method == 'POST':
        # issue book
        form = IssueBookForm(request.form)

        book_id = int(request.form.get("book"))
        issued_to = request.form.get("issued_to")
        issued_to_user = User.query.filter_by(userid=issued_to).first()

        bookissuance = BookIssuanceTracker.query.filter_by(book=book_id, issued_to=None).first()
        book = Book.query.filter_by(id=book_id).first()
        bookissuance.issued_to = issued_to
        bookissuance.bookissuance.availablenoofcopies -= 1  ## using backreference
        bookissuance.issuance_date = datetime.now()
        bookissuance.to_be_returned_by_date = datetime.now() + timedelta(days=7)
        db.session.commit()

        bookIssuanceHistory = BookIssuanceHistory(book=book_id,
                                                  title=book.title,
                                                  authors=book.authors,
                                                  publisher=book.publisher,
                                                  edition=book.edition,
                                                  isbn=book.isbn,
                                                  userid=issued_to_user.userid,
                                                  username=issued_to_user.username,
                                                  issuance_date=bookissuance.issuance_date,
                                                  actual_return_date=None,
                                                  returnstatus="PENDING_RETURN"
                                                  )

        try:

            db.session.add(bookIssuanceHistory)
            db.session.commit()


        except:
            flash("Unable to commit", "success")

        flash("Book issued ")
        users = User.query.all()
        return render_template(
            "lms/issuebook.html", books=Book.query.all(), users=users, form=form)


@lms_bp.route("/returnbook", methods=["GET", "POST"])
@login_required
def returnbook():
    if request.method == 'GET':
        form = IssueBookForm(request.form)
        # list the books

        booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.actual_return_date == None,BookIssuanceTracker.issued_to != None).all()


        if booksissued:
            return render_template("lms/returnbook.html", booksissued=booksissued, form=form)
        flash("No Return Pending")
        return render_template(
            "lms/returnbook.html", booksissued=booksissued,
            form=form)

    if request.method == 'POST':
        # issue book
        form = IssueBookForm(request.form)
        datetimenow = datetime.now()

        book_id = int(request.form.get("book"))
        issued_to = request.form.get("issued_to")
        issued_to_user = User.query.filter_by(userid=issued_to).all()

        bookissuance = BookIssuanceTracker.query.filter_by(book=book_id).first()



        bookissuedto = bookissuance.issued_to
        issuance_date = bookissuance.issuance_date

        bookissuance.issued_to = None
        bookissuance.bookissuance.availablenoofcopies += 1  ## using backreference
        bookissuance.issuance_date = None
        bookissuance.to_be_returned_by_date = None
        bookissuance.actual_return_date = datetimenow
        bookissuance.returnstatus = "RETURNED"
        db.session.commit()
        flash("Book Returned ")

        try:
            # using issuance date as part of filter to identify the record
            bookissuance = BookIssuanceHistory.query.filter_by(book=book_id, userid=bookissuedto,
                                                               issuance_date=issuance_date).first()

            bookissuance.actual_return_date = datetimenow
            bookissuance.returnstatus = "RETURNED"

            db.session.commit()


        except Exception as error:

            print(error)
            flash("Unable to commit" + str(error), "success")

        booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.actual_return_date == None,BookIssuanceTracker.issued_to != None).all()

        return render_template(
            "lms/returnbook.html",
            booksissued=booksissued,
            form=form)


@lms_bp.route("/renewbook", methods=["GET", "POST"])
@login_required
def renewbook():
    if request.method == 'GET':
        form = IssueBookForm(request.form)
        # list the books which are issued for renewal screen
        booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.issued_to != None).all()

        if booksissued:
            return render_template("lms/renewbook.html", booksissued=booksissued, form=form)
        flash("No Return Pending")
        return render_template(
            "lms/renewbook.html", booksissued=booksissued, form=form)

    if request.method == 'POST':
        # issue book
        form = RenewBookForm(request.form)

        book_id = int(request.form.get("book"))

        bookissuance = BookIssuanceTracker.query.filter_by(book=book_id).first()

        # bookissuance.bookissuance.availablenoofcopies += 1  ## using backreference
        bookissuedto = bookissuance.issued_to
        issuance_date = bookissuance.issuance_date
        newreturndate = datetime.now() + timedelta(days=7)

        # bookissuance.issuance_date = datetime.now()
        bookissuance.to_be_returned_by_date = newreturndate
        db.session.commit()

        flash("Book Re-Issued")
        booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.issued_to != None).all()

        try:
            # using issuance date as part of filter to identify the record
            bookissuance = BookIssuanceHistory.query.filter_by(book=book_id, userid=bookissuedto,
                                                               issuance_date=issuance_date).first()

            bookissuance.actual_return_date = None

            db.session.commit()



        except Exception as error:

            print(error)
            flash("Unable to commit" + str(error), "success")
            booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.issued_to != None).all()

        return render_template(
            "lms/renewbook.html", booksissued=booksissued,
            form=form)


@lms_bp.route("/issuedbooks", methods=["GET", "POST"])
@login_required
def issuedbook():
    if request.method == 'GET':
        booksissued = BookIssuanceTracker.query.filter(BookIssuanceTracker.issued_to != None).all()
        # booksissued = BookIssuanceTracker.query.filter_by(issued_to=current_user.userid).all()
        if booksissued:
            return render_template("lms/issuedbooks.html", booksissued=booksissued)
        flash("No Books issued")
        return render_template(
            "lms/issuedbooks.html",
            booksissued = booksissued)

    if request.method == 'POST':
        # issue book

        return render_template(
            "lms/issuedbooks.html",
            booksissued= BookIssuanceTracker.query.filter(BookIssuanceTracker.issued_to != None).all())


@lms_bp.route("/searchbooks", methods=["GET", "POST"])
@login_required
def searchbook():
    if request.method == 'GET':
        form = SearchBookForm(request.form)
        # list the books
        books = Book.query.filter().all()
        if books:
            return render_template("lms/searchbook.html", searchresult=Book.query.filter().all(), form=form)
        flash("Books Available in system are listed. Use search option to search with book title")
        return render_template(
            "lms/searchbook.html", searchresult=Book.query.all(), form=form)

    if request.method == 'POST':
        # issue book
        form = SearchBookForm(request.form)

        title = str(request.form.get("title"))

        searchresult=Book.query.filter(or_(Book.title.contains(title),Book.authors.contains(title),Book.isbn.contains(title))).all()
        if searchresult:
            return render_template("lms/searchbook.html", searchresult=searchresult, form=form)
        flash("No Books matching name or authors or isbn")
        return render_template(
            "lms/searchbook.html", searchresult=searchresult, form=form)


@lms_bp.route("/listmembers", methods=["GET", "POST"])
@login_required
def listmembers():
    if request.method == 'GET':
        form = UpdateForm(request.form)
        users = User.query.filter_by().all()
        if users:
            return render_template("lms/memberlist.html", users=users, form=form)
        flash("user list")
        return render_template(
            "lms/memberlist.html",
            users=users)

    if request.method == 'POST':
        userid = int(request.form.get("book"))

        user = User.query.filter_by(userid=userid).first()
        form = UpdateForm(request.form)

        form.userid.data = user.userid
        form.username.data = user.username
        form.mobile.data = user.mobile
        form.email.data = user.email

        return render_template("authentication/updateuser.html", form=form)









@lms_bp.route("/bookhistory", methods=["GET", "POST"])
@login_required
def bookhistory():
    if request.method == 'GET':
        bookrecords = BookIssuanceHistory.query.filter_by().all()
        if bookrecords:
            return render_template("lms/bookhistory.html", bookrecords=bookrecords)
        flash("No Records Available")
        return render_template(
            "lms/bookhistory.html",
            bookrecords=bookrecords)
