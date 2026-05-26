import click
from flask.cli import AppGroup

from app.admin.services import create_admin_account

admin_cli = AppGroup("admin", help="Admin account management.")


@admin_cli.command("create")
@click.option("--username", prompt=True, help="Admin username.")
@click.password_option("--password", confirmation_prompt=True)
def create_admin(username, password):
    """Create a new admin account. Prompts for username and password."""
    try:
        admin = create_admin_account(username, password)
    except ValueError as error:
        raise click.ClickException(str(error))
    click.echo(f"Admin '{admin.username}' created (id={admin.id}).")
