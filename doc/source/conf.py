# -*- coding: utf-8 -*-
#

# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.viewcode',
              'sphinxcontrib.rsvgconverter',
              'oslo_policy.sphinxext',
              'oslo_policy.sphinxpolicygen',
              'oslo_config.sphinxext',
              'oslo_config.sphinxconfiggen']

try:
    import openstackdocstheme
    extensions.append('openstackdocstheme')
except ImportError:
    openstackdocstheme = None

repository_name = 'openstack/ironic-inspector'
use_storyboard = True

wsme_protocols = ['restjson']

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
copyright = u'OpenStack Developers'

config_generator_config_file = '../../tools/config-generator.conf'
sample_config_basename = '_static/ironic-inspector'

policy_generator_config_file = '../../tools/policy-generator.conf'
sample_policy_basename = '_static/ironic-inspector'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
#from ironic import version as ironic_version
# The full version, including alpha/beta/rc tags.
#release = ironic_version.version_info.release_string()
# The short X.Y version.
#version = ironic_version.version_info.version_string()

# A list of ignored prefixes for module index sorting.
modindex_common_prefix = ['ironic.']

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# NOTE(cinerama): mock out nova modules so docs can build without warnings
#import mock
#import sys
#MOCK_MODULES = ['nova', 'nova.compute', 'nova.context']
#for module in MOCK_MODULES:
#    sys.modules[module] = mock.Mock()

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
if openstackdocstheme is not None:
    html_theme = 'openstackdocs'
else:
    html_theme = 'default'
#html_theme_path = ["."]
#html_theme = '_theme'
#html_static_path = ['_static']

# Output file base name for HTML help builder.
htmlhelp_basename = 'ironic-inspectordoc'

latex_use_xindy = False

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    (
        'index',
        'doc-ironic-inspector.tex',
        u'Ironic Inspector Documentation',
        u'OpenStack Foundation',
        'manual'
    ),
]

# -- Options for seqdiag ------------------------------------------------------

seqdiag_html_image_format = "SVG"
