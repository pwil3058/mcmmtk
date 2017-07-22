#  Copyright 2017 Peter Williams <pwil3058@gmail.com>
#
# This software is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2 of the License only.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; if not, write to:
#  The Free Software Foundation, Inc., 51 Franklin Street,
#  Fifth Floor, Boston, MA 02110-1301 USA

"""A modellor's view of paint"""

__all__ = []
__author__ = "Peter Williams <pwil3058@gmail.com>"

import re
from gi.repository import Gtk

from .gtx import actions

from .epaint import gpaint
from .epaint import pchar
from .epaint import pedit
from .epaint import pmix
from .epaint import pseries
from .epaint import standards
from .epaint import vpaint

class ModelPaint(vpaint.Paint):
    COLOUR = vpaint.HCV
    class CHARACTERISTICS(pchar.Characteristics):
        NAMES = ("transparency", "finish", "metallic", "fluorescence")
    EXTRAS = [vpaint.EXTRA("notes", _("Notes:"), "")]

class ModelTargetColour(vpaint.TargetColour):
    COLOUR = ModelPaint.COLOUR

class ModelPaintListStore(gpaint.PaintListStore):
    COLUMN_DEFS = [gpaint.TNS(_("Colour Name"), "name", {"resizable" : True, "expand" : True}, lambda row: row[0].name)] + \
        gpaint.paint_extras_tns_list(ModelPaint) + \
        [   gpaint.TNS(_("Hue"), "hue", {}, lambda row: row[0].hue),
            gpaint.TNS(_("Chr."), "chroma", {}, lambda row: row[0].chroma),
            gpaint.TNS(_("Val."), "value", {}, lambda row: row[0].value),
        ] + gpaint.paint_characteristics_tns_list(ModelPaint)

class ModelPaintListView(gpaint.PaintListView):
    MODEL = ModelPaintListStore

class ModelPaintEditor(pedit.PaintEditor):
    PAINT = ModelPaint

class ModelMixture(pmix.Mixture):
    PAINT = ModelPaint

class MixedModelPaint(pmix.MixedPaint):
    MIXTURE = ModelMixture

class MatchedModelPaintListStore(pmix.MatchedPaintListStore):
    COLUMN_DEFS = [
            gpaint.TNS(_("Value"), "value", {}, lambda row: row[0].value),
            gpaint.TNS(_("Hue"), "hue", {}, lambda row: row[0].hue),
        ] + gpaint.paint_characteristics_tns_list(ModelPaint)

class MixedModelPaintInformationDialogue(pmix.MixedPaintInformationDialogue):
    class COMPONENT_LIST_VIEW(pmix.MixedPaintComponentsListView):
        class MODEL(pmix.MixedPaintComponentsListStore):
            COLUMN_DEFS = ModelPaintListStore.COLUMN_DEFS[1:]

class MatchedModelPaintListView(pmix.MatchedPaintListView):
    UI_DESCR = """
    <ui>
        <popup name="paint_list_popup">
            <menuitem action="show_paint_details"/>
            <menuitem action="remove_selected_paints"/>
        </popup>
    </ui>
    """
    MODEL = MatchedModelPaintListStore
    MIXED_PAINT_INFORMATION_DIALOGUE = MixedModelPaintInformationDialogue

MODEL_NC_MATCHER = re.compile(r'^NamedColour\(name=(".+"), rgb=(.+), transparency="(.+)", finish="(.+)"\)$')

class ModelPaintSeries(pseries.PaintSeries):
    @staticmethod
    def paints_fm_definition(lines):
        from .epaint.rgbh import RGB8, RGB16, RGBPN
        paints = list()
        if len(lines):
            old_model_matcher = re.compile("(^[^:]+):\s+(RGB\([^)]+\)), (Transparency\([^)]+\)), (Finish\([^)]+\))$")
            if old_model_matcher.match(lines[0]):
                # Old format
                # TODO: remove support for old paint series format
                RGB = collections.namedtuple("RGB", ["red", "green", "blue"])
                colours = []
                for line in lines:
                    match = old_model_matcher.match(line)
                    if not match:
                        raise cls.ParseError(_("Badly formed definition: {0}.").format(line))
                    # Old data files were wx and hence 8 bits per channel
                    # so we need to convert them to 16 bist per channel
                    rgb = [channel << 8 for channel in eval(match.group(2))]
                    paints.append(ModelPaint(match.group(1), rgb, eval(match.group(3)), eval(match.group(4))))
            elif MODEL_NC_MATCHER.match(lines[0]):
                RGB = ModelPaint.COLOUR.RGB
                colours = []
                for line in lines:
                    match = MODEL_NC_MATCHER.match(line)
                    if not match:
                        raise cls.ParseError(_("Badly formed definition: {0}.").format(line))
                    name = eval(match.group(1))
                    rgb = eval(match.group(2))
                    kwargs = {"metallic": "NM", "fluorescence": "NF"}
                    for extra in ModelPaint.EXTRAS:
                        kwargs[extra.name] = extra.default_value
                    paints.append(ModelPaint(name, rgb, transparency=match.group(3), finish=match.group(4), **kwargs))
            else:
                RGB = ModelPaint.COLOUR.RGB
                for line in lines:
                    try:
                        paints.append(eval(line))
                    except TypeError as edata:
                        raise cls.ParseError(_("Badly formed definition: {0}. ({1})").format(line, str(edata)))
        return paints


class ModelPaintSelector(pseries.PaintSelector):
    class SELECT_PAINT_LIST_VIEW (ModelPaintListView):
        UI_DESCR = """
        <ui>
            <popup name="paint_list_popup">
                <menuitem action="add_paint_to_mixer"/>
                <menuitem action="add_paints_to_mixer"/>
                <menuitem action="show_paint_details"/>
            </popup>
        </ui>
        """
        def populate_action_groups(self):
            """
            Populate action groups ready for UI initialization.
            """
            self.action_groups[actions.AC_SELN_MADE].add_actions(
                [
                    ("add_paints_to_mixer", Gtk.STOCK_ADD, _("Add Selection"), None,
                     _("Add the selected paints to the mixer."),),
                ]
            )
            self.action_groups[actions.AC_SELN_NONE|self.AC_CLICKED_ON_ROW].add_actions(
                [
                    ("add_paint_to_mixer", Gtk.STOCK_ADD, None, None,
                     _("Add the clicked paint to the mixer."),),
                ]
            )

class ModelPaintSeriesManager(pseries.PaintSeriesManager):
    PAINT_SELECTOR = ModelPaintSelector
    PAINT_COLLECTION = ModelPaintSeries

class ModelPaintStandard(standards.PaintStandard):
    PAINT = ModelPaint
    @classmethod
    def paints_fm_definition(cls, lines):
        # this has to be defined here to SEE ModelPaint in eval()
        from .epaint.rgbh import RGB8, RGB16, RGBPN
        RGB = cls.PAINT.COLOUR.RGB
        paints = list()
        for line in lines:
            try:
                paints.append(eval(line))
            except TypeError as edata:
                raise cls.ParseError(_("Badly formed definition: {0}. ({1})").format(line, str(edata)))
        return paints

class SelectStandardModelPaintListView(standards.SelectStandardPaintListView):
    MODEL = ModelPaintListStore

class StandardModelPaintSelector(standards.StandardPaintSelector):
    SELECT_STANDARD_PAINT_LIST_VIEW = SelectStandardModelPaintListView

class ModelPaintStandardsManager(standards.PaintStandardsManager):
    STANDARD_PAINT_SELECTOR = StandardModelPaintSelector
    PAINT_STANDARD_COLLECTION = ModelPaintStandard
