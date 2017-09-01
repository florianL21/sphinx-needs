import os
import json

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst import Directive
from jinja2 import Template


class Needimport(nodes.General, nodes.Element):
    pass


class NeedimportDirective(Directive):
    has_content = False

    required_arguments = 1
    optional_arguments = 0

    option_spec = {'version': directives.nonnegative_int,
                   'hide': directives.flag,
                   'filter': directives.unicode_code,
                   'id_prefix': directives.unicode_code,
                   'tags': directives.unicode_code
                   }

    final_argument_whitespace = True

    def run(self):
        needs_list = {}
        version = self.options.get("version", None)
        filter = self.options.get("filter", None)
        id_prefix = self.options.get("id_prefix", "")
        hide = True if "hide" in self.options.keys() else False

        tags = self.options.get("tags", [])
        if len(tags) > 0:
            tags = [tag.strip() for tag in tags.split(";")]

        env = self.state.document.settings.env

        need_import_path = self.arguments[0]

        if not os.path.isabs(need_import_path):
            need_import_path = os.path.join(env.app.confdir, need_import_path)

        if not os.path.exists(need_import_path):
            raise FileNotFoundError("Could not load needs import file {0}".format(need_import_path))

        with open(need_import_path, "r") as needs_file:
            needs_file_content = needs_file.read()
        try:
            needs_import_list = json.loads(needs_file_content)
        except json.JSONDecodeError as e:
            # ToDo: Add exception handling
            raise e

        if version is None:
            try:
                version = needs_import_list["current_version"]
                if not isinstance(version, str):
                    raise KeyError
            except KeyError:
                raise CorruptedNeedsFile("Key 'current_version' missing or corrupted in {0}".format(need_import_path))
        if version not in needs_import_list["versions"].keys():
            raise VersionNotFound("Version {0} not found in needs import file {1}".format(version, need_import_path))

        needs_list = needs_import_list["versions"][version]["needs"]

        # If we need to set an id prefix, we also need to manipulate all used ids in the imported data.
        if id_prefix != "":
            needs_ids = needs_list.keys()

            for key, need in needs_list.items():
                for id in needs_ids:
                    # Manipulate links
                    if id in need["links"]:
                        for n, link in enumerate(need["links"]):
                            if id == link:
                                need["links"][n] = "".join([id_prefix, id])
                    # Manipulate descriptions
                    # ToDo: Use regex for better matches.
                    need["description"] = need["description"].replace(id, "".join([id_prefix, id]))

        # tags update
        for key, need in needs_list.items():
            need["tags"] = need["tags"] + tags

        template_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "needimport_template.rst")
        with open(template_location, "r") as template_file:
            template_content = template_file.read()
        template = Template(template_content)
        content = template.render(needs_list=needs_list, hide=hide, id_prefix=id_prefix)
        self.state_machine.insert_input(content.split('\n'),
                                        self.state_machine.document.attributes['source'])

        return []


class VersionNotFound(BaseException):
    pass


class CorruptedNeedsFile(BaseException):
    pass
