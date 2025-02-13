import click
import win32api
import win32print

@click.group()
def cli():
    pass

@click.command()
def show_printers():
    all_printers = [printer[2] for printer in win32print.EnumPrinters(6)]
    click.echo('Available Printers:')
    for i, printer in enumerate(all_printers, start=1):
        click.echo(f"{i}. {printer}")

@click.command()
def dropdb():
    click.echo('Dropped the database')


cli.add_command(show_printers)
cli.add_command(dropdb)


if __name__ == "__main__":
    cli()
