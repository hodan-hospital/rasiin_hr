import re

import frappe
import requests
from frappe import _


POWER_BI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
AZURE_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
POWER_BI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


@frappe.whitelist()
def get_embed_config(report_url=None, report_id=None, workspace_id=None):
	"""Return the embed configuration needed by the Power BI JS client."""
	settings = _get_power_bi_settings()
	context = _resolve_report_context(
		report_url=report_url or settings.get("report_url"),
		report_id=report_id or settings.get("report_id"),
		workspace_id=workspace_id or settings.get("workspace_id"),
	)
	access_token = _get_azure_access_token(settings)
	report = _get_report_metadata(access_token, context)
	embed_token = _generate_embed_token(access_token, context)

	return {
		"report_id": context["report_id"],
		"workspace_id": context.get("workspace_id"),
		"report_name": report.get("name"),
		"report_url": context.get("report_url"),
		"embed_url": report.get("embedUrl"),
		"access_token": embed_token.get("token"),
		"token_expiration": embed_token.get("expiration"),
		"token_type": "Embed",
	}


def _get_power_bi_settings():
	doctype_settings = _get_power_bi_settings_from_doctype()
	settings = {
		"tenant_id": doctype_settings.get("tenant_id") or frappe.conf.get("power_bi_tenant_id"),
		"client_id": doctype_settings.get("client_id") or frappe.conf.get("power_bi_client_id"),
		"client_secret": doctype_settings.get("client_secret") or frappe.conf.get("power_bi_client_secret"),
		"workspace_id": doctype_settings.get("workspace_id") or frappe.conf.get("power_bi_workspace_id"),
		"report_id": doctype_settings.get("report_id") or frappe.conf.get("power_bi_report_id"),
		"report_url": doctype_settings.get("report_url") or frappe.conf.get("power_bi_report_url"),
	}

	missing = [key for key in ("tenant_id", "client_id", "client_secret") if not settings.get(key)]
	if missing:
		frappe.throw(
			_("Missing Power BI settings: {0}").format(", ".join(missing))
		)

	return settings


def _get_power_bi_settings_from_doctype():
	if not frappe.db.exists("DocType", "Powerbi Settings"):
		return {}

	doc = frappe.get_cached_doc("Powerbi Settings")
	return {
		"tenant_id": doc.tenant_id,
		"client_id": doc.client_id,
		"client_secret": doc.get_password("client_secret", raise_exception=False),
		"workspace_id": doc.workspace_id,
		"report_id": doc.report_id,
		"report_url": doc.report_url,
	}


def _resolve_report_context(report_url=None, report_id=None, workspace_id=None):
	parsed_report_id = None
	parsed_workspace_id = None

	if report_url:
		parsed_report_id = _extract_report_id(report_url)
		parsed_workspace_id = _extract_workspace_id(report_url)

	final_report_id = report_id or parsed_report_id
	final_workspace_id = workspace_id or parsed_workspace_id

	if not final_report_id:
		frappe.throw(
			_("Missing Power BI report id. Set it in Power BI Settings, site_config.json, or pass a valid report URL.")
		)

	# Service principal embedding needs a real workspace id; "me" cannot be used.
	if final_workspace_id == "me":
		if not workspace_id:
			frappe.throw(
				_(
					"Power BI embed token flow needs the real workspace id. Add workspace_id in Power BI Settings or power_bi_workspace_id in site_config.json instead of using groups/me."
				)
			)
		final_workspace_id = workspace_id

	return {
		"report_id": final_report_id,
		"workspace_id": final_workspace_id,
		"report_url": report_url,
	}


def _extract_report_id(report_url):
	match = re.search(r"/reports/([a-f0-9-]+)", report_url or "", re.IGNORECASE)
	return match.group(1) if match else None


def _extract_workspace_id(report_url):
	match = re.search(r"/groups/([^/]+)", report_url or "", re.IGNORECASE)
	return match.group(1) if match else None


def _get_azure_access_token(settings):
	response = requests.post(
		AZURE_TOKEN_URL.format(tenant_id=settings["tenant_id"]),
		data={
			"grant_type": "client_credentials",
			"client_id": settings["client_id"],
			"client_secret": settings["client_secret"],
			"scope": POWER_BI_SCOPE,
		},
		timeout=30,
	)
	data = _parse_response(response, "Azure AD token")
	token = data.get("access_token")

	if not token:
		frappe.throw(_("Azure AD token response did not include an access_token."))

	return token


def _get_report_metadata(access_token, context):
	response = requests.get(
		_get_report_endpoint(context),
		headers=_build_power_bi_headers(access_token),
		timeout=30,
	)
	data = _parse_response(response, "Power BI report metadata")

	if not data.get("embedUrl"):
		frappe.throw(_("Power BI report metadata did not include an embedUrl."))

	return data


def _generate_embed_token(access_token, context):
	response = requests.post(
		f"{_get_report_endpoint(context)}/GenerateToken",
		headers=_build_power_bi_headers(access_token),
		json={"accessLevel": "View", "allowSaveAs": False},
		timeout=30,
	)
	return _parse_response(response, "Power BI embed token")


def _get_report_endpoint(context):
	if context.get("workspace_id"):
		return (
			f"{POWER_BI_API_BASE}/groups/{context['workspace_id']}/reports/{context['report_id']}"
		)

	return f"{POWER_BI_API_BASE}/reports/{context['report_id']}"


def _build_power_bi_headers(access_token):
	return {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/json",
	}


def _parse_response(response, label):
	try:
		payload = response.json()
	except ValueError:
		payload = None

	if response.ok:
		return payload or {}

	message = (response.text or "").strip() or response.reason or f"HTTP {response.status_code}"
	if isinstance(payload, dict):
		error = payload.get("error")
		if isinstance(error, dict):
			message = error.get("message") or error.get("code") or message
		elif error:
			message = str(error)
		elif payload.get("message"):
			message = payload.get("message")

	hint = ""
	if label == "Power BI report metadata":
		if response.status_code == 401:
			hint = _(
				" Check the Azure app credentials and confirm the Power BI tenant allows service principals to use Power BI APIs."
			)
		elif response.status_code == 403:
			hint = _(
				" Check that the service principal or its security group has access to the workspace and report."
			)
		elif response.status_code == 404:
			hint = _(
				" Check that workspace_id and report_id are correct and that the report is in a shared workspace, not My Workspace."
			)

	frappe.throw(
		_("{0} request failed ({1}): {2}{3}").format(
			label,
			response.status_code,
			message,
			hint,
		)
	)
