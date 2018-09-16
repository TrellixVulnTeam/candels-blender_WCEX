import os
from pathlib import Path

import click
import numpy as np

from blender import segmap

IMG_TMP = 'blend_{:06d}.npy'
SEG_TMP = 'blend_seg_{:06d}.npy'
IMG_DTYPE = np.float32
SEG_DTYPE = np.uint8


def concatenate_img(path, with_labels=False):
    n_img = len(list(path.glob('blend_seg*npy')))

    img0 = np.load(path / IMG_TMP.format(0))
    imgmain = np.empty((n_img, *img0.shape[:-1]), dtype=img0.dtype)
    if with_labels:
        img_indiv = np.empty((n_img, *img0.shape), dtype=img0.dtype)

    with click.progressbar(range(n_img),
                           label='Loading stamps') as bar:
        for idx in bar:
            img = np.load(path / IMG_TMP.format(idx))
            imgmain[idx] = img.sum(axis=-1)
            if with_labels:
                # Channels last
                img_indiv[idx, ...] = img

    np.save(path / 'images.npy', imgmain.astype(IMG_DTYPE))

    if with_labels:
        np.save(path / 'labels.npy', img_indiv.astype(IMG_DTYPE))


def concatenate_seg(path, method=None):
    n_img = len(list(path.glob('blend_seg*npy')))

    method = method or segmap_identity

    if isinstance(method, str):
        method = getattr(segmap, method)

    img0 = method(np.load(path / SEG_TMP.format(0)))
    imgmain = np.empty((n_img, *img0.shape), dtype=img0.dtype)

    with click.progressbar(range(n_img),
                           label='Loading masks') as bar:
        for idx in bar:
            seg = np.load(path / SEG_TMP.format(idx))
            imgmain[idx] = method(seg)

    np.save(path / 'labels.npy', imgmain.astype(SEG_DTYPE))


def segmap_identity(array):
    return array.astype(SEG_DTYPE)


@click.command()
@click.argument('image_dir', type=click.Path(exists=True))
@click.argument('method',
                type=click.Choice(['background_overlap_galaxies',
                                   'overlap_galaxies',
                                   'individual_galaxy_images']))
@click.option('--delete', is_flag=True,
              help="Delete individual images once finished")
def main(image_dir, method, delete):
    """
    Concatenate the individual blended sources and masks from IMAGE_DIR
    into two files `images.npy` and `labels.npy`.

    `image.npy` (32 bits) contains the stacked blend images

    `labels.npy` (bool) contains the labels produced from the masks
    with the given METHOD

    """
    path = Path.cwd() / image_dir
    image_file = path / 'images.npy'
    label_file = path / 'labels.npy'

    if not image_file.exists():
        if method == 'individual_galaxy_images':
            concatenate_img(path, with_labels=True)
        else:
            concatenate_img(path)
        click.echo('Stamps concatenated')

    if method != 'individual_galaxy_images':
        if not label_file.exists():
            concatenate_seg(path, method=method)
            click.echo('Segmentation maps concatenated')

    if delete:
        for img in path.glob('blend_*.npy'):
            os.remove(img)
        click.echo('Individual stamps deleted')


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
