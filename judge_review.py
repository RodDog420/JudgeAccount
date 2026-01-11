from app import create_app, db
from app.models import Judge, Review, MediaLink, User

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Judge': Judge, 'Review': Review, 'MediaLink': MediaLink, 'User': User}