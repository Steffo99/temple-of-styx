import flask as f

blueprint = f.Blueprint('health', __name__, template_folder='templates')


@blueprint.route("/")
def healthcheck():
    if f.request.accept_mimetypes.accept_html:
        return f.render_template("healthcheck.html")
    elif f.request.accept_mimetypes.accept_json:
        return f.jsonify(True)
    else:
        return f.abort(406)


__all__ = (
    "blueprint",
)
