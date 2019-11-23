# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from functools import partial

import click

from . import forward, velocity

click.option = partial(click.option, show_default=True)


@click.group()
@click.pass_context
def cli(ctx):
    ctx.ensure_object(dict)


cli.add_command(forward.fwd)
cli.add_command(velocity.vp)


def main():
    cli(obj={})
