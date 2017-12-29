from setuptools import setup, find_packages

name = 'onegov.quill'
description = (
    'Quill rich text editor integration for OneGov.'
)
version = '0.2.3'


def get_long_description():
    readme = open('README.rst').read()
    history = open('HISTORY.rst').read()

    # cut the part before the description to avoid repetition on pypi
    readme = readme[readme.index(description) + len(description):]

    return '\n'.join((readme, history))


setup(
    name=name,
    version=version,
    description=description,
    long_description=get_long_description(),
    url='http://github.com/OneGov/onegov.quill',
    author='Seantis GmbH',
    author_email='info@seantis.ch',
    license='GPLv2',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=name.split('.')[:-1],
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    python_requires='>=3.6',
    install_requires=[
        'bleach',
        'more.webassets>=0.3.2',
        'onegov.core>=0.4.0',
        'wtforms'
    ],
    extras_require=dict(
        test=[
            'coverage',
            'onegov_testing',
            'onegov.form',
            'pytest',
        ],
    ),
    entry_points={
        'onegov': [
            'upgrade = onegov.quill.upgrade'
        ]
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    ]
)
