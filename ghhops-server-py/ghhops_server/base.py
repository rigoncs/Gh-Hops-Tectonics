"""Base types for Hops middleware"""
import sys
import traceback
import os
import os.path as op
import inspect
import json
import base64
from typing import Tuple

from ghhops_server.logger import hlogger
from ghhops_server.component import HopsComponent


DEFAULT_CATEGORY = "Hops"
DEFAULT_SUBCATEGORY = "Hops Python"


class HopsBase:
    """Base class for all Hops middleware implementations"""

    ROOT_ROUTE = "/"
    SOLVE_ROUTE = "/solve"

    BUILTIN_ROUTES = [ROOT_ROUTE, SOLVE_ROUTE]

    ERROR_PAGE_405 = """<!doctype html>
<html lang=en>
<title>405 Method Not Allowed</title>
<h1>Method Not Allowed</h1>
<p>The method is not allowed for the requested URL.</p>"""

    def __init__(self, app):
        self.app = app
        # components dict store each components two times under
        # two keys get uri and solve uri, for faster lookups in query and solve
        # it is assumed that uri and solve uri and both unique to the component
        self._components: dict[str, HopsComponent] = {}

    def handles(self, request):
        uri = request.path
        return uri in HopsBase.BUILTIN_ROUTES or uri in self._components

    def handle_HEAD(self, _):
        return self._prep_response(200, "Success")

    def handle_GET(self, request):
        uri = request.path

        # if calling GET /solve, respond 405
        if self._is_solve_uri(uri):
            return self._return_method_not_allowed()

        # if component exists, return component data
        res, results = self.query(uri=uri)
        if res:
            response = self._prep_response()
            response.data = results

        # otherwise return 404
        else:
            response = self._prep_response(404, "Unknown URI")

        return response

    def handle_POST(self, request):
        uri = request.path

        # if POST on component uri, return 405
        if self._is_comp_uri(uri):
            return self._return_method_not_allowed()

        # otherwise try to solve with payload
        data = request.data
        res, results = self.solve(uri=uri, payload=data)
        if res:
            response = self._prep_response()
            response.data = results.encode(encoding="utf_8")

        # otherwise return 404
        else:
            response = self._prep_response(404, "Execution Error")
            response.data = results.encode(encoding="utf_8")

        return response

    def _is_solve_uri(self, uri):
        return uri == HopsBase.SOLVE_ROUTE

    def _is_comp_uri(self, uri):
        return uri in self._components

    def query(self, uri) -> Tuple[bool, str]:
        """Get information on given uri"""
        # try to find a component registered for this uri
        # returns one object {}
        comp = self._components.get(uri, None)
        if comp:
            hlogger.debug("Getting component metadata: %s", comp)
            return True, self._get_comp_data(comp)

        # try to find a collection of components in this uri
        # returns list of objects [{},{},...]
        comps = [c for c in self._components.values() if c.uri.startswith(uri)]
        if comps:
            hlogger.debug("Getting a list of all registered components")
            return True, self._get_comps_data(comps)

        return False, self._return_with_err("Unknown Hops url")

    def solve(self, uri, payload) -> Tuple[bool, str]:
        """Perform Solve on given uri"""
        if uri == HopsBase.ROOT_ROUTE:
            hlogger.debug("Nothing to solve on root")
            return False, self._return_with_err("Nothing to solve on root")

        # FIXME: remove support for legacy solve behaviour
        elif uri == HopsBase.SOLVE_ROUTE:
            data = json.loads(payload)
            comp_uri = data["pointer"]
            if not comp_uri.startswith(HopsBase.ROOT_ROUTE):
                comp_uri = HopsBase.ROOT_ROUTE + comp_uri
            for comp in self._components.values():
                if comp_uri == comp.uri:
                    hlogger.info("Solving using legacy API: %s", comp)
                    return self._process_solve_request(comp, payload)

        # FIXME: test this new api
        else:
            comp = self._components.get(uri, None)
            if comp:
                hlogger.info("Solving: %s", comp)
                return self._process_solve_request(comp, payload)
        return False, self._return_with_err("Unknown Hops component url")

    def _return_with_err(self, err_msg, res_dict=None):
        err_res = res_dict
        if err_res:
            err = err_res.get("errors", None)
            if isinstance(err, list):
                err.append(err_msg)
            else:
                err_res["errors"] = [err_msg]
        else:
            err_res = {"values": [], "errors": [err_msg]}

        return json.dumps(err_res, cls=_HopsEncoder)

    def _return_method_not_allowed(self):
        response = self._prep_response(405, "Method Not Allowed")
        response.data = HopsBase.ERROR_PAGE_405.encode(encoding="utf_8")
        return response

    def _get_all_comps_data(self):
        # return json formatted string of all components metadata
        return json.dumps(list(self._components.values()), cls=_HopsEncoder)

    def _get_comps_data(self, comps):
        # return json formatted string of all components metadata
        return json.dumps(comps, cls=_HopsEncoder)

    def _get_comp_data(self, comp):
        # return json formatted string of component metadata
        return json.dumps(comp, cls=_HopsEncoder)

    def _prepare_icon(self, resource_path, icon_file_path):
        # return icon data in base64 for embedding in http results
        # determine possible icon paths
        possible_icon_paths = []
        if op.isabs(icon_file_path):
            possible_icon_paths.append(icon_file_path)
        else:
            process_icon_file_path = op.join(os.getcwd(), icon_file_path)
            possible_icon_paths.append(process_icon_file_path)
            if resource_path:
                sidecar_icon_file_path = op.join(resource_path, icon_file_path)
                possible_icon_paths.append(sidecar_icon_file_path)

        for icon_path in possible_icon_paths:
            if op.exists(icon_path):
                with open(icon_path, "rb") as image_file:
                    base64_bytes = base64.b64encode(image_file.read())
                    return base64_bytes.decode("ascii")

        hlogger.error(
            "Can not find icon file at %s",
            ", ".join(possible_icon_paths)
        )

    def _process_solve_request(self, comp, payload) -> Tuple[bool, str]:
        # parse payload for inputs
        res, inputs = self._prepare_inputs(comp, payload)
        if not res:
            hlogger.debug("Bad inputs: %s", inputs)
            return res, self._return_with_err("Bad inputs")

        # run
        try:
            solve_returned = self._solve(comp, inputs)
            hlogger.debug("Return data: %s", solve_returned)
            res, outputs = self._prepare_outputs(comp, solve_returned)
            return (
                res,
                outputs if res else self._return_with_err("Bad outputs"),
            )
        except Exception as solve_ex:
            # try to grab traceback data and create err msg
            _, _, exc_traceback = sys.exc_info()
            try:
                fmt_tb = traceback.format_tb(exc_traceback)
                # FIXME: can we safely assume we are only 2 levels in stack?
                ex_msg = "\n".join(fmt_tb[2:])
                ex_msg = str(solve_ex) + f"\n{ex_msg}"
            except Exception:
                # otherwise use exception str as msg
                ex_msg = str(solve_ex)

            hlogger.debug("Exception occured in handler: %s", ex_msg)
            return False, self._return_with_err(
                "Exception occured in handler:\n%s" % ex_msg
            )

    def _prepare_inputs(self, comp, payload) -> Tuple[bool, list]:
        # parse input payload
        data = json.loads(payload)

        # grab input param data and value items
        # FIXME: this works on a single branch only? ["0"][0]
        param_values = {}
        for item in data["values"]:
            param_values[item["ParamName"]] = item

        inputs = []
        for in_param in comp.inputs:
            if in_param.name not in param_values and not in_param.optional:
                return (
                    False,
                    f"Missing value for required input {in_param.name}",
                )
            in_param_data = param_values[in_param.name]
            value = in_param.from_input(in_param_data)
            inputs.append(value)

        if len(comp.inputs) != len(param_values):
            return (
                False,
                "Input count does not match number of inputs for component",
            )

        return True, inputs

    def _solve(self, comp, inputs):
        return comp.handler(*inputs)

    def _prepare_outputs(self, comp, returns) -> Tuple[bool, str]:
        outputs = []
        if not isinstance(returns, tuple):
            returns = (returns,)
        for out_param, out_result in zip(comp.outputs, returns):
            output_data = out_param.from_result(out_result)
            outputs.append(output_data)
        payload = {"values": outputs}
        hlogger.debug("Return payload: %s", payload)
        return True, json.dumps(payload, cls=_HopsEncoder)

    def component(
        self,
        rule=None,
        name=None,
        nickname=None,
        description=None,
        category=None,
        subcategory=None,
        icon=None,
        inputs=None,
        outputs=None,
    ):
        """Decorator for Hops middleware"""

        def __func_wrapper__(comp_func):
            # determine path of the caller file
            # this is used for resource resolution
            frame = inspect.stack()[1]
            module = inspect.getmodule(frame[0])
            resource_path = None
            if module and module.__file__:
                resource_path = op.dirname(module.__file__)

            # register python func as Hops component
            if inputs:
                # inspect default parameters in function signature
                f_sig = inspect.signature(comp_func)
                f_params = f_sig.parameters.values()
                if len(inputs) != len(f_params):
                    raise Exception(
                        "Number of function parameters is "
                        "different from defined Hops inputs"
                    )
                # apply function param default values in order
                # to defined Hops inputs. this will override any
                # previously defined default values
                for hinput, fparam in zip(inputs, f_params):
                    if fparam.default != inspect.Parameter.empty:
                        hinput.default = fparam.default

            # determine name, and uri
            comp_name = name or comp_func.__qualname__
            uri = rule or f"/{comp_name}"
            # grab icon data
            icon_data = None
            if icon:
                icon_data = self._prepare_icon(resource_path, icon)
            # create component instance
            comp = HopsComponent(
                uri=uri,
                name=comp_name,
                nickname=nickname,
                desc=description or comp_func.__doc__,
                cat=category or DEFAULT_CATEGORY,
                subcat=subcategory or DEFAULT_SUBCATEGORY,
                icon=icon_data,
                inputs=inputs or [],
                outputs=outputs or [],
                handler=comp_func,
            )
            hlogger.debug("Component registered: %s", comp)
            # register by uri and solve uri, for fast lookup on query and solve
            self._components[uri] = comp
            self._components[comp.solve_uri] = comp
            return comp_func

        return __func_wrapper__


class _HopsEncoder(json.JSONEncoder):
    """Custom json encoder to properly encode RhinoCommon and Hops types"""

    def default(self, o):
        if hasattr(o, "Encode"):
            return o.Encode()
        elif hasattr(o, "encode"):
            return o.encode()
        return json.JSONEncoder.default(self, o)
