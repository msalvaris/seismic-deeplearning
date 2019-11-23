# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from functools import partial

import click
import h5py
import numpy as np

from deepseismic_imaging.forward import Receiver, RickerSource, TimeAxis, VelocityModel

click.option = partial(click.option, show_default=True)


@click.group()
@click.argument("input", type=click.Path())
@click.argument("output", type=click.Path())
@click.option(
    "-d", "--duration", default=1000.0, type=float, help="Simulation duration (in ms)",
)
@click.option("-dt", default=2.0, type=float, help="Time increment (in ms)")
@click.option("--n-pml", default=10, type=int, help="PML size (in grid points)")
@click.option(
    "--n-receivers", default=11, type=int, help="Number of receivers per horizontal dimension",
)
@click.option("--space-order", default=2, type=int, help="Space order")
@click.option("--spacing", default=10.0, type=float, help="Spacing between grid points")
@click.pass_context
def fwd(
    ctx,
    dt: float,
    duration: float,
    input: str,
    n_pml: int,
    n_receivers: int,
    output: str,
    space_order: int,
    spacing: float,
):
    """Forward modelling"""
    if dt:
        ctx.obj["dt"] = dt
    ctx.obj["duration"] = duration
    ctx.obj["input_file"] = h5py.File(input, mode="r")
    ctx.obj["n_pml"] = n_pml
    ctx.obj["n_receivers"] = n_receivers
    ctx.obj["output_file"] = h5py.File(output, mode="w")
    ctx.obj["space_order"] = space_order
    ctx.obj["spacing"] = spacing


@fwd.command()
@click.option("-f0", default=0.01, type=float, help="Source peak frequency (in kHz)")
@click.pass_context
def ricker(ctx, f0: float):
    """Ricker source"""
    input_file = ctx.obj["input_file"]
    output_file = ctx.obj["output_file"]
    n = sum(len(x.values()) for x in input_file.values())
    with click.progressbar(length=n) as bar:
        for input_group_name, input_group in input_file.items():
            for dataset in input_group.values():
                first_dataset = dataset
                break
            model = VelocityModel(
                shape=first_dataset.shape,
                origin=tuple(0.0 for _ in first_dataset.shape),
                spacing=tuple(ctx.obj["spacing"] for _ in first_dataset.shape),
                vp=first_dataset[()],
                space_order=ctx.obj["space_order"],
                n_pml=ctx.obj["n_pml"],
            )
            time_range = TimeAxis(start=0.0, stop=ctx.obj["duration"], step=ctx.obj["dt"])
            source = RickerSource(name="source", grid=model.grid, f0=f0, npoint=1, time_range=time_range,)
            source.coordinates.data[0, :] = np.array(model.domain_size) * 0.5
            source.coordinates.data[0, -1] = 0.0
            n_receivers = ctx.obj["n_receivers"]
            total_receivers = n_receivers ** (len(model.shape) - 1)
            receivers = Receiver(name="receivers", grid=model.grid, npoint=total_receivers, time_range=time_range,)
            receivers_coords = np.meshgrid(
                *(np.linspace(start=0, stop=s, num=n_receivers + 2)[1:-1] for s in model.domain_size[:-1])
            )
            for d in range(len(receivers_coords)):
                receivers.coordinates.data[:, d] = receivers_coords[d].flatten()
            receivers.coordinates.data[:, -1] = 0.0
            output_group = output_file.create_group(input_group_name)
            for input_dataset_name, vp in input_group.items():
                model.vp = vp[()]
                seismograms = model.solve(source=source, receivers=receivers, time_range=time_range)
                output_group.create_dataset(input_dataset_name, data=seismograms)
                bar.update(1)
