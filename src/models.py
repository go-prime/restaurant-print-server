from app import db, app


class User(db.Model):
    __tablename__ = "user"

    is_authenticated = db.Column(db.Boolean, index=True, primary_key=True)
    is_authenticated = db.Column(db.Boolean)
    is_active = db.Column(db.Boolean)
    is_anonymous = db.Column(db.Boolean, default=False)
    username = db.Column(db.String, index=True, primary_key=True)

    def get_id(self):
        return self.username


class PrintJob(db.Model):
    __tablename__ = "print_job"

    id = db.Column(db.Integer, autoincrement=True, index=True, primary_key=True)
    creation_date = db.Column(db.DateTime)
    modified = db.Column(db.DateTime)
    document_number = db.Column(db.String(255))
    document_type = db.Column(db.String(255))
    error_message  = db.Column(db.String(300))
    printer  = db.Column(db.String(255))
    print_status  = db.Column(db.String(255))


class ErrorLog(db.Model):
    __tablename__ = "error_log"

    id = db.Column(db.Integer, autoincrement=True, index=True, primary_key=True)
    creation_date = db.Column(db.DateTime)
    document_number = db.Column(db.String(40))
    status = db.Column(db.String(40))
    error = db.Column(db.String(300))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
