"""
The implementation of base data structure to host various settings collected
from external source with built-in validation and schema translation support.

The main reasons for such incapsulation are to
 - apply in one place all data validation actions (for attributes and values)
 - introduce internal information schema (names of attribues) to remove dependency
 with data structrure, formats, names from external sources (e.g. AGIS/CRIC)


:author: Alexey Anisenkov
:contact: anisyonk@cern.ch
:date: January 2018
"""

import logging
logger = logging.getLogger(__name__)


class BaseData(object):
    """
        High-level object to host structured data collected from external source
        It's cosidered to be like a bridge (connector) in order to remove direct dependency to
        external schema (format) implementation
    """

    _keys = {}

    def _load_data(self, data, kmap={}, validators=None):
        """
            Construct and initialize data from ext source.

            :param data: input dictionary of queue data settings
            :param kmap: the translation map of data attributes from external format to internal schema
            :param validators: map of validation handlers to be applied
        """

        # the translation map of the queue data attributes from external data to internal schema
        # 'internal_name':('ext_name1', 'extname2_if_any')
        # 'internal_name2':'ext_name3'

        # first defined ext field will be used
        # if key is not explicitly specified then ext name will be used as is
        ## fix me later to proper internal names if need

        #kmap = {
        #    # 'internal_name':('ext_name1', 'extname2_if_any'),
        #    # 'internal_name2':'ext_name3'
        #    }

        if validators is None:
            # default validators
            validators = {int: self.clean_numeric,
                          str: self.clean_string,
                          bool: self.clean_boolean,
                          dict: self.clean_dictdata,

                          None: self.clean_string,  # default validator
                          }

        for ktype, knames in self._keys.iteritems():

            for kname in knames:
                raw, value = None, None

                ext_names = kmap.get(kname) or kname
                if isinstance(ext_names, basestring):
                    ext_names = [ext_names]
                for name in ext_names:
                    raw = data.get(name)
                    if raw is not None:
                        break

                ## cast to required type and apply default validation
                hvalidator = validators.get(ktype, validators.get(None))
                if callable(hvalidator):
                    value = hvalidator(raw, ktype, kname)
                ## apply custom validation if defined
                hvalidator = getattr(self, 'clean__%s' % kname, None)
                if callable(hvalidator):
                    value = hvalidator(raw, value)

                setattr(self, kname, value)

    ##
    ## default validators
    ##
    def clean_numeric(self, raw, ktype, kname=None, defval=0):
        """
            Clean and convert input value to requested numeric type
            :param raw: raw input data
            :param ktype: variable type to which result should be casted
            :param defval: default value to be used in case of cast error
        """

        if isinstance(raw, ktype):
            return raw

        if isinstance(raw, basestring):
            raw = raw.strip()
        try:
            return ktype(raw)
        except Exception:
            logger.warning('failed to convert data for key=%s, raw=%s to type=%s' % (kname, raw, ktype))
            return defval

    def clean_string(self, raw, ktype, kname=None, defval=""):
        """
            Clean and convert input value to requested string type
            :param raw: raw input data
            :param ktype: variable type to which result should be casted
            :param defval: default value to be used in case of cast error
        """

        if isinstance(raw, ktype):
            return raw

        if isinstance(raw, basestring):
            raw = raw.strip()
        elif raw is None:
            return defval
        try:
            return ktype(raw)
        except Exception:
            logger.warning('failed to convert data for key=%s, raw=%s to type=%s' % (kname, raw, ktype))
            return defval

    def clean_boolean(self, raw, ktype, kname=None, defval=None):
        """
            Clean and convert input value to requested boolean type
            :param raw: raw input data
            :param ktype: variable type to which result should be casted
            :param defval: default value to be used in case of cast error
        """

        if isinstance(raw, ktype):
            return raw

        val = str(raw).strip().lower()
        allowed_values = ['', 'none', 'true', 'false', 'yes', 'no', '1', '0']

        if val not in allowed_values:
            logger.warning('failed to convert data for key=%s, raw=%s to type=%s' % (kname, raw, ktype))
            return defval

        return raw.lower() in ['1', 'true', 'yes']

    def clean_dictdata(self, raw, ktype, kname=None, defval=None):
        """
            Clean and convert input value to requested dict type
            :param raw: raw input data
            :param ktype: variable type to which result should be casted
            :param defval: default value to be used in case of cast error
        """

        if isinstance(raw, ktype):
            return raw

        elif raw is None:
            return defval
        try:
            return ktype(raw)
        except Exception:
            logger.warning('failed to convert data for key=%s, raw=%s to type=%s' % (kname, raw, ktype))
            return defval

    ## custom function pattern to apply extra validation to the give key values
    #def clean__keyname(self, raw, value):
    #  :param raw: raw value passed from ext source as input
    #  :param value: preliminary cleaned and casted to proper type value
    #
    #    return value

    def __repr__(self):
        """
            Default representation of an object
        """

        ret = []
        attrs = [key for key in dir(self) if not callable(getattr(self, key)) and not key.startswith('_')]
        for key in sorted(attrs):
            ret.append(" %s=%s" % (key, getattr(self, key)))
        ret.append('')
        return '\n'.join(ret)