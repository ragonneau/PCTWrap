"""PCTWrap: PyCUTEst wrapper for Python

PCTWrap is open-source wrapper for the package PyCUTEst, that ease its use.

"""
from datetime import datetime

from .problems import PCTProblem
from .wrapper import PCTWrapper
from .version import __version__

__all__ = ['PCTProblem', 'PCTWrapper']
__author__ = 'Tom M. Ragonneau'
if datetime.now().year == 2020:
    __copyright__ = 'Copyright %d, Tom M. Ragonneau' % datetime.now().year
else:
    __copyright__ = 'Copyright 2020-%d, Tom M. Ragonneau' % datetime.now().year
__credits__ = ['Tom M. Ragonneau']
__license__ = 'LGPLv3+'
__date__ = 'December, 2020'
__maintainer__ = 'Tom M. Ragonneau'
__email__ = 'tom.ragonneau@connect.polyu.hk'
__status__ = 'Beta'
