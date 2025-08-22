app_name = "immo"
app_title = "Immo"
app_publisher = "IntraPro"
app_description = "Immobilier"
app_email = "admin@medigo.one"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "immo",
# 		"logo": "/assets/immo/logo.png",
# 		"title": "Immo",
# 		"route": "/immo",
# 		"has_permission": "immo.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/immo/css/immo.css"
# app_include_js = "/assets/immo/js/immo.js"

# include js, css files in header of web template
# web_include_css = "/assets/immo/css/immo.css"
# web_include_js = "/assets/immo/js/immo.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "immo/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "immo/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "immo.utils.jinja_methods",
# 	"filters": "immo.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "immo.install.before_install"
# after_install = "immo.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "immo.uninstall.before_uninstall"
# after_uninstall = "immo.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "immo.utils.before_app_install"
# after_app_install = "immo.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "immo.utils.before_app_uninstall"
# after_app_uninstall = "immo.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "immo.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Location Longue Duree": {
		"on_update": "immo.hooks_handlers.location_longue_duree.on_update",
		"on_cancel": "immo.hooks_handlers.location_longue_duree.on_cancel",
		"validate": "immo.hooks_handlers.location_longue_duree.validate"
	},
	"Location Courte Duree": {
		"on_update": "immo.hooks_handlers.location_courte_duree.on_update",
		"on_trash": "immo.hooks_handlers.location_courte_duree.on_trash",
		"after_delete": "immo.hooks_handlers.location_courte_duree.after_delete",
		"validate": "immo.hooks_handlers.location_courte_duree.validate",
		"after_insert": "immo.hooks_handlers.location_courte_duree.after_insert"
	},
	"Mensualite": {
		"on_update": "immo.hooks_handlers.mensualite.on_update",
		"on_cancel": "immo.hooks_handlers.mensualite.on_cancel",
		"validate": "immo.hooks_handlers.mensualite.validate"
	},
	"Charge": {
		"on_update": "immo.hooks_handlers.charge.on_update",
		"on_cancel": "immo.hooks_handlers.charge.on_cancel",
		"validate": "immo.hooks_handlers.charge.validate"
	},
	"Commission": {
		"on_update": "immo.hooks_handlers.commission.on_update",
		"on_submit": "immo.hooks_handlers.commission.on_submit",
		"on_cancel": "immo.hooks_handlers.commission.on_cancel",
		"validate": "immo.hooks_handlers.commission.validate"
	},
	"Paiement Locataire": {
		"on_update": "immo.hooks_handlers.paiement_locataire.on_update",
		"after_insert": "immo.hooks_handlers.paiement_locataire.after_insert",
		"on_trash": "immo.hooks_handlers.paiement_locataire.on_trash",
		"on_submit": "immo.hooks_handlers.paiement_locataire.on_submit",
		"on_cancel": "immo.hooks_handlers.paiement_locataire.on_cancel",
		"validate": "immo.hooks_handlers.paiement_locataire.validate"
	},
	"Paiement Proprietaire": {
		"on_update": "immo.hooks_handlers.paiement_proprietaire.on_update",
		"after_insert": "immo.hooks_handlers.paiement_proprietaire.after_insert",
		"on_trash": "immo.hooks_handlers.paiement_proprietaire.on_trash",
		"on_submit": "immo.hooks_handlers.paiement_proprietaire.on_submit",
		"on_cancel": "immo.hooks_handlers.paiement_proprietaire.on_cancel",
		"validate": "immo.hooks_handlers.paiement_proprietaire.validate"
	},
	"Location Bloc": {
		"on_update": "immo.hooks_handlers.location_bloc.on_update",
		"on_trash": "immo.hooks_handlers.location_bloc.on_trash",
		"validate": "immo.hooks_handlers.location_bloc.validate"
	},
	"Paiement Bloc": {
		"on_update": "immo.hooks_handlers.paiement_bloc.on_update",
		"on_trash": "immo.hooks_handlers.paiement_bloc.on_trash",
		"validate": "immo.hooks_handlers.paiement_bloc.validate"
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"immo.tasks.all"
# 	],
# 	"daily": [
# 		"immo.tasks.daily"
# 	],
# 	"hourly": [
# 		"immo.tasks.hourly"
# 	],
# 	"weekly": [
# 		"immo.tasks.weekly"
# 	],
# 	"monthly": [
# 		"immo.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "immo.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "immo.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "immo.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["immo.utils.before_request"]
# after_request = ["immo.utils.after_request"]

# Job Events
# ----------
# before_job = ["immo.utils.before_job"]
# after_job = ["immo.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"immo.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

