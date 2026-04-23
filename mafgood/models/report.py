from extensions import db
from datetime import datetime


class Report(db.Model):
    __tablename__ = 'reports'

    id          = db.Column(db.Integer, primary_key=True)
    reason      = db.Column(db.String(500), nullable=False)
    status      = db.Column(db.String(20),  default='pending')  # pending / reviewed / dismissed
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign keys
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'),  nullable=False)
    item_id     = db.Column(db.Integer, db.ForeignKey('items.id'),  nullable=False)

    def get_report_details(self) -> str:
        return (
            f"Report #{self.id} | Item: {self.item_id} | "
            f"Reason: {self.reason} | Status: {self.status}"
        )

    def to_dict(self):
        return {
            'id':          self.id,
            'reason':      self.reason,
            'status':      self.status,
            'reporter_id': self.reporter_id,
            'item_id':     self.item_id,
            'created_at':  self.created_at.isoformat(),
        }

    def __repr__(self):
        return f'<Report {self.id} on Item {self.item_id}>'
