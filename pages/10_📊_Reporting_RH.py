import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import warnings
import os
import unicodedata
from utils import compute_promise_refusal_rate_row

warnings.filterwarnings("ignore")


st.set_page_config(
	page_title="📊 Reporting RH",
	page_icon="📊",
	layout="wide",
)

# Bloquer l'accès si l'utilisateur n'est pas connecté (même logique que les autres pages)
if not st.session_state.get("logged_in", False):
	st.stop()


TITLE_FONT = dict(family="Arial, sans-serif", size=18, color="#111111")


def _parse_mixed_dates(series: pd.Series) -> pd.Series:
	"""Parser robuste pour les dates mixtes (texte, formats Excel, etc.)."""
	s = series.copy()
	try:
		if pd.api.types.is_numeric_dtype(s):
			def _maybe_excel(x: object) -> "pd.Timestamp | pd.NaTType":
				try:
					xf = float(x)  # type: ignore[arg-type]
					return pd.Timestamp("1899-12-30") + pd.Timedelta(days=xf)
				except Exception:
					return pd.NaT

			# Construire une série à partir d'une compréhension pour éviter les conflits de typage dans apply
			converted = [
				_maybe_excel(v)
				if pd.notna(v) and str(v).strip().replace(".", "", 1).isdigit()
				else pd.NaT
				for v in s
			]
			excel_series = pd.Series(converted, index=s.index)
			return excel_series.combine_first(
				pd.to_datetime(s, dayfirst=True, errors="coerce")
			)
	except Exception:
		pass

	parsed = pd.to_datetime(s, dayfirst=True, errors="coerce")
	if parsed.isna().sum() > len(parsed) * 0.25:
		parsed_alt = pd.to_datetime(s, errors="coerce")
		parsed = parsed.combine_first(parsed_alt)
	return parsed


def _truncate_label(label: str, max_len: int = 20) -> str:
	"""Couper proprement les libellés trop longs pour les graphiques."""
	if not isinstance(label, str):
		return label
	if len(label) <= max_len:
		return label
	return label[: max_len - 4].rstrip() + "...."


def apply_title_style(fig):
	"""Appliquer un style homogène aux titres Plotly."""
	try:
		fig.update_layout(title_font=TITLE_FONT)
	except Exception:
		try:
			current = ""
			if hasattr(fig.layout, "title") and getattr(fig.layout.title, "text", None):
				current = fig.layout.title.text
			fig.update_layout(title=dict(text=current, x=0, xanchor="left", font=TITLE_FONT))
		except Exception:
			pass
	try:
		fig.update_traces(textfont=dict(size=15))
	except Exception:
		pass
	try:
		if hasattr(fig.layout, "legend"):
			fig.update_layout(legend=dict(font=dict(size=13)))
	except Exception:
		pass
	return fig


def render_generic_metrics(metrics):
	"""Row de cartes KPI (HTML) utilisé pour les tuiles principales.

	metrics: liste de tuples (titre, valeur, couleur_hex)
	"""
	css = """
	<style>
	.gen-kpi-row{display:flex;gap:18px;justify-content:center;align-items:stretch;margin-bottom:8px}
	.gen-kpi{background:#fff;border-radius:8px;padding:14px 18px;min-width:220px;flex:0 1 auto;border:1px solid #e6eef6;box-shadow:0 2px 6px rgba(0,0,0,0.04);display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
	.gen-kpi .t{font-size:17px;color:#2c3e50;margin-bottom:8px;font-weight:700;text-align:center}
	.gen-kpi .v{font-size:36px;color:#172b4d;font-weight:800;text-align:center}
	</style>
	"""
	cards = []
	for title, value, color in metrics:
		cards.append(
			f"<div class='gen-kpi'><div class='t'>{title}</div><div class='v' style='color:{color};'>{value}</div></div>"
		)
	html = css + "<div class='gen-kpi-row'>" + "".join(cards) + "</div>"
	return html


def create_global_filters(df_recrutement: pd.DataFrame):
	"""Filtres globaux Entité / Direction / Période de recrutement & demande."""
	if df_recrutement is None or len(df_recrutement) == 0:
		return {}

	filters = {}
	left_col, right_col = st.sidebar.columns(2)

	entites = ["Toutes"] + sorted(df_recrutement["Entité demandeuse"].dropna().unique())
	with left_col:
		filters["entite"] = st.selectbox("Entité demandeuse", entites, key="rrh_entite")

	directions = ["Toutes"] + sorted(df_recrutement["Direction concernée"].dropna().unique())
	with right_col:
		filters["direction"] = st.selectbox("Direction concernée", directions, key="rrh_direction")

	left_col2, right_col2 = st.sidebar.columns(2)

	# Période de recrutement (année d'entrée effective)
	with left_col2:
		if "Date d'entrée effective du candidat" in df_recrutement.columns:
			df_recrutement["Année_Recrutement"] = df_recrutement[
				"Date d'entrée effective du candidat"
			].dt.year  # type: ignore[attr-defined]
			annees_rec = sorted(
				[
					y
					for y in df_recrutement["Année_Recrutement"].dropna().unique()
					if not pd.isna(y)
				]
			)
			if annees_rec:
				filters["periode_recrutement"] = st.selectbox(
					"Période de recrutement",
					["Toutes"] + [int(a) for a in annees_rec],
					index=len(annees_rec),
					key="rrh_periode_rec",
				)
			else:
				filters["periode_recrutement"] = "Toutes"
		else:
			filters["periode_recrutement"] = "Toutes"

	# Période de la demande (année de réception)
	date_demande_col = "Date de réception de la demande aprés validation de la DRH"
	with right_col2:
		if date_demande_col in df_recrutement.columns:
			df_recrutement["Année_Demande"] = df_recrutement[date_demande_col].dt.year  # type: ignore[attr-defined]
			annees_dem = sorted(
				[
					y
					for y in df_recrutement["Année_Demande"].dropna().unique()
					if not pd.isna(y)
				]
			)
			if annees_dem:
				filters["periode_demande"] = st.selectbox(
					"Période de la demande",
					["Toutes"] + [int(a) for a in annees_dem],
					index=len(annees_dem),
					key="rrh_periode_dem",
				)
			else:
				filters["periode_demande"] = "Toutes"
		else:
			filters["periode_demande"] = "Toutes"

	return filters


def apply_global_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
	"""Appliquer les filtres globaux aux données."""
	df_filtered = df.copy()

	if filters.get("entite") != "Toutes":
		df_filtered = df_filtered[df_filtered["Entité demandeuse"] == filters["entite"]]

	if filters.get("direction") != "Toutes":
		df_filtered = df_filtered[df_filtered["Direction concernée"] == filters["direction"]]

	if (
		filters.get("periode_recrutement") != "Toutes"
		and "Année_Recrutement" in df_filtered.columns
	):
		df_filtered = df_filtered[
			df_filtered["Année_Recrutement"] == filters["periode_recrutement"]
		]

	if (
		filters.get("periode_demande") != "Toutes"
		and "Année_Demande" in df_filtered.columns
	):
		df_filtered = df_filtered[
			df_filtered["Année_Demande"] == filters["periode_demande"]
		]

	return df_filtered


def load_data_from_files(csv_file=None, excel_file=None):
	"""Charger et préparer les données depuis fichiers ou sources déjà synchronisées.

	Même logique que dans Espace Test pour garantir un comportement identique.
	"""
	df_integration = None
	df_recrutement = None
	try:
		# CSV (intégrations) – optionnel ici
		if csv_file is not None:
			df_integration = pd.read_csv(csv_file)
		else:
			local_csv = "2025-10-09T20-31_export.csv"
			if os.path.exists(local_csv):
				df_integration = pd.read_csv(local_csv)

		if df_integration is not None and "Date Intégration" in df_integration.columns:
			df_integration["Date Intégration"] = pd.to_datetime(
				df_integration["Date Intégration"]
			)

		# Excel (recrutement)
		try:
			if (
				"synced_recrutement_df" in st.session_state
				and st.session_state.synced_recrutement_df is not None
			):
				df_recrutement = st.session_state.synced_recrutement_df.copy()
			elif excel_file is not None:
				df_recrutement = pd.read_excel(excel_file, sheet_name=0)
			else:
				import glob

				excel_files = glob.glob("Recrutement global PBI All*.xlsx")
				if excel_files:
					excel_files.sort(key=os.path.getmtime)
					latest_excel = excel_files[-1]
					df_recrutement = pd.read_excel(latest_excel, sheet_name=0)
				else:
					local_excel = "Recrutement global PBI All  google sheet (5).xlsx"
					if os.path.exists(local_excel):
						df_recrutement = pd.read_excel(local_excel, sheet_name=0)
		except Exception as e:
			st.error(f"Erreur lors du chargement des données de recrutement: {e}")

		if df_recrutement is not None:
			date_columns = [
				"Date de réception de la demande aprés validation de la DRH",
				"Date d'entrée effective du candidat",
				"Date d'annulation /dépriorisation de la demande",
				"Date de la 1er réponse du demandeur à l'équipe RH",
				"Date du 1er retour equipe RH  au demandeur",
				"Date de désistement",
				"Date d'acceptation du candidat",
				"Date d'entrée prévisionnelle",
			]

			for col in date_columns:
				if col in df_recrutement.columns:
					try:
						df_recrutement[col] = _parse_mixed_dates(df_recrutement[col])
					except Exception:
						df_recrutement[col] = pd.to_datetime(
							df_recrutement[col], errors="coerce"
						)

			df_recrutement.columns = df_recrutement.columns.str.strip()

			critical_cols = [
				"Poste demandé",
				"Direction concernée",
				"Entité demandeuse",
				"Statut de la demande",
			]
			for col in critical_cols:
				if col in df_recrutement.columns:
					df_recrutement[col] = (
						df_recrutement[col].astype(str).str.strip()
					)

			numeric_columns = ["Nb de candidats pré-selectionnés"]
			for col in numeric_columns:
				if col in df_recrutement.columns:
					df_recrutement[col] = pd.to_numeric(
						df_recrutement[col], errors="coerce"
					).fillna(0)

			required_cols = [
				"Statut de la demande",
				"Poste demandé",
				"Direction concernée",
				"Entité demandeuse",
				"Modalité de recrutement",
			]
			missing = [c for c in required_cols if c not in df_recrutement.columns]
			if missing:
				st.warning(
					f"Colonnes attendues manquantes dans le fichier de recrutement: {missing}"
				)

		return df_integration, df_recrutement

	except Exception as e:
		st.error(f"Erreur lors du chargement des données: {e}")
		return None, None


def render_plotly_scrollable(fig, max_height: int = 500):
	"""Affichage Plotly dans un conteneur scrollable (pour longues listes)."""
	from streamlit import components

	try:
		html = fig.to_html(full_html=False, include_plotlyjs="cdn")
		injected_css = """
		<style>
		.plotly .gtitle, .plotly .gtitle text { font-family: Arial, sans-serif !important; font-size: 18px !important; fill: #111111 !important; }
		.plotly .gtitle { text-anchor: start !important; }
		.streamlit-plotly-wrapper{ display:flex; justify-content:flex-start; }
		</style>
		"""
		wrapper = f"""
<div class='streamlit-plotly-wrapper' style='width:100%;'>
  {injected_css}
  {html}
</div>
"""
		components.v1.html(wrapper, height=max_height, scrolling=True)
	except Exception:
		fig = apply_title_style(fig)
		st.plotly_chart(fig, use_container_width=True)


def create_recrutements_clotures_tab(df_recrutement: pd.DataFrame, global_filters: dict):
	"""Bloc Recrutements Clôturés avec KPI dont le taux de refus.

	Le KPI "Taux de refus des promesses d'embauche (%)" est calculé comme dans
	Espace Test, en prenant en compte les filtres globaux (entité, direction,
	période de recrutement basée sur Date de désistement / Date d'acceptation).
	"""

	# Filtrer sur les demandes clôturées pour les graphes principaux
	df_cloture = df_recrutement[
		df_recrutement["Statut de la demande"] == "Clôture"
	].copy()

	if len(df_cloture) == 0:
		st.warning("Aucune donnée de recrutement clôturé disponible")
		return

	df_filtered = apply_global_filters(df_cloture, global_filters)

	recrutements = len(df_filtered)
	postes_uniques = df_filtered["Poste demandé"].nunique()
	directions_uniques = df_filtered["Direction concernée"].nunique()

	date_reception_col = "Date de réception de la demande aprés validation de la DRH"
	date_retour_rh_col = "Date du 1er retour equipe RH  au demandeur"
	delai_display = "N/A"
	delai_help = "Colonnes manquantes ou pas de durées valides"
	if date_reception_col in df_filtered.columns and date_retour_rh_col in df_filtered.columns:
		try:
			s = pd.to_datetime(df_filtered[date_reception_col], errors="coerce")
			e = pd.to_datetime(df_filtered[date_retour_rh_col], errors="coerce")
			mask = s.notna() & e.notna()
			if mask.sum() > 0:
				durees = (e[mask] - s[mask]).dt.days
				durees = durees[durees >= 0]
				if len(durees) > 0:
					delai_moyen = round(durees.mean(), 1)
					delai_display = f"{delai_moyen}"
					delai_help = f"Moyenne calculée sur {len(durees)} recrutements clôturés"
		except Exception:
			pass

	metrics_html = render_generic_metrics(
		[
			("Nombre de recrutements", recrutements, "#1f77b4"),
			("Postes concernés", postes_uniques, "#2ca02c"),
			("Nombre de Directions concernées", directions_uniques, "#ff7f0e"),
			("Délai moyen recrutement (jours)", delai_display, "#6f42c1"),
		]
	)
	st.markdown(metrics_html, unsafe_allow_html=True)

	col1, col2 = st.columns([2, 1])

	with col1:
		if "Date d'entrée effective du candidat" in df_filtered.columns:
			df_filtered["Mois_Année"] = (
				df_filtered["Date d'entrée effective du candidat"]
				.dt.to_period("M")
				.dt.to_timestamp()
			)
			monthly_data = df_filtered.groupby("Mois_Année").size().rename("Count")
			if not monthly_data.empty:
				all_months = pd.date_range(
					start=monthly_data.index.min(),
					end=monthly_data.index.max(),
					freq="MS",
				)
				monthly_data = monthly_data.reindex(all_months, fill_value=0)
				monthly_data = (
					monthly_data.reset_index()
					.rename(columns={"index": "Mois_Année"})
				)
				monthly_data["Mois_Année"] = monthly_data["Mois_Année"].dt.strftime(
					"%b %Y"
				)

				fig_evolution = px.bar(
					monthly_data,
					x="Mois_Année",
					y="Count",
					title="Évolution des recrutements",
					text="Count",
				)
				fig_evolution.update_traces(
					marker_color="#1f77b4",
					textposition="inside",
					texttemplate="<b>%{y}</b>",
					textfont=dict(size=15, color="white"),
					hovertemplate="%{y}<extra></extra>",
				)
				fig_evolution.update_layout(
					height=360,
					margin=dict(t=48, b=30, l=20, r=20),
					xaxis_title=None,
					yaxis_title=None,
					xaxis=dict(
						tickmode="array",
						tickvals=monthly_data["Mois_Année"],
						ticktext=monthly_data["Mois_Année"],
						tickangle=45,
					),
				)
				fig_evolution = apply_title_style(fig_evolution)
				st.plotly_chart(fig_evolution, use_container_width=True)

	with col2:
		if "Modalité de recrutement" in df_filtered.columns:
			modalite_data = df_filtered["Modalité de recrutement"].value_counts()
			fig_modalite = go.Figure(
				data=[
					go.Pie(
						labels=modalite_data.index,
						values=modalite_data.values,
						hole=0.5,
						textposition="inside",
						textinfo="percent",
					)
				]
			)
			fig_modalite.update_traces(textfont=dict(size=14))
			fig_modalite.update_layout(
				title=dict(
					text="Répartition par Modalité de recrutement",
					x=0,
					xanchor="left",
					font=TITLE_FONT,
				),
				height=380,
				legend=dict(
					orientation="v",
					yanchor="middle",
					y=0.5,
					xanchor="left",
					x=1.0,
					font=dict(size=14),
				),
				margin=dict(l=20, r=140, t=60, b=20),
			)
			fig_modalite = apply_title_style(fig_modalite)
			st.plotly_chart(fig_modalite, use_container_width=True)

	col3, col4 = st.columns(2)

	with col3:
		direction_counts = df_filtered["Direction concernée"].value_counts()
		df_direction = (
			direction_counts.rename_axis("Direction").reset_index(name="Count")
		)
		df_direction = df_direction.sort_values("Count", ascending=False)
		df_direction["Label_trunc"] = df_direction["Direction"].apply(
			lambda s: _truncate_label(s, max_len=24)
		)
		df_direction["Label_display"] = df_direction["Label_trunc"].astype(str) + "\u00A0\u00A0"

		fig_direction = px.bar(
			df_direction,
			x="Count",
			y="Label_display",
			title="Comparaison par direction",
			text="Count",
			orientation="h",
			custom_data=["Direction"],
		)
		fig_direction.update_traces(
			marker_color="grey",
			textposition="inside",
			texttemplate="<b>%{x}</b>",
			textfont=dict(size=14, color="white"),
			textangle=0,
			hovertemplate="<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>",
			constraintext="none",
		)
		fig_direction.update_layout(
			height=300,
			xaxis_title=None,
			yaxis_title=None,
			margin=dict(l=160, t=48, b=30, r=20),
			xaxis=dict(tickangle=0),
			yaxis=dict(
				automargin=True,
				tickfont=dict(size=15),
				ticklabelposition="outside left",
				categoryorder="array",
				categoryarray=list(df_direction["Label_display"][::-1]),
			),
			title=dict(
				text="<b>Comparaison par direction</b>",
				x=0,
				xanchor="left",
				font=TITLE_FONT,
			),
			uniformtext=dict(minsize=10, mode="show"),
		)
		fig_direction = apply_title_style(fig_direction)
		render_plotly_scrollable(fig_direction, max_height=320)

	with col4:
		poste_counts = df_filtered["Poste demandé"].value_counts()
		df_poste = poste_counts.rename_axis("Poste").reset_index(name="Count")
		df_poste = df_poste.sort_values("Count", ascending=False)
		df_poste["Label_trunc"] = df_poste["Poste"].apply(
			lambda s: _truncate_label(s, max_len=24)
		)
		df_poste["Label_display"] = df_poste["Label_trunc"].astype(str) + "\u00A0\u00A0"
		fig_poste = px.bar(
			df_poste,
			x="Count",
			y="Label_display",
			title="Comparaison par poste",
			text="Count",
			orientation="h",
			custom_data=["Poste"],
		)
		fig_poste.update_traces(
			marker_color="grey",
			textposition="inside",
			texttemplate="<b>%{x}</b>",
			textfont=dict(size=14, color="white"),
			textangle=0,
			hovertemplate="<b>%{customdata[0]}</b><br>Nombre: %{x}<extra></extra>",
			constraintext="none",
		)
		height_poste = max(320, 28 * len(df_poste))
		fig_poste.update_layout(
			height=height_poste,
			xaxis_title=None,
			yaxis_title=None,
			margin=dict(l=160, t=48, b=30, r=20),
			xaxis=dict(tickangle=0),
			yaxis=dict(
				automargin=True,
				tickfont=dict(size=15),
				ticklabelposition="outside left",
				categoryorder="array",
				categoryarray=list(df_poste["Label_display"][::-1]),
			),
			title=dict(
				text="<b>Comparaison par poste</b>",
				x=0,
				xanchor="left",
				font=TITLE_FONT,
			),
			uniformtext=dict(minsize=10, mode="show"),
		)
		fig_poste = apply_title_style(fig_poste)
		render_plotly_scrollable(fig_poste, max_height=320)

	col5, col6 = st.columns(2)

	with col5:
		try:
			candidats_series = pd.to_numeric(
				df_filtered["Nb de candidats pré-selectionnés"], errors="coerce"
			).fillna(0)
			total_candidats = int(candidats_series.sum())
		except (KeyError, ValueError):
			total_candidats = 0

		st.markdown(
			"<div style='font-family:Arial,sans-serif; font-size:18px; font-weight:700; "
			"color:#111111; text-align:left; margin:8px 0 4px 0;'>"
			"Nombre de candidats présélectionnés</div>",
			unsafe_allow_html=True,
		)

		fig_candidats = go.Figure(
			go.Indicator(
				mode="gauge+number",
				value=total_candidats,
				gauge={
					"axis": {"range": [0, max(total_candidats * 2, 100)], "visible": True},
					"bar": {"color": "green"},
				},
			)
		)
		fig_candidats.update_layout(
			height=260, margin=dict(t=10, b=10, l=20, r=20)
		)
		st.plotly_chart(fig_candidats, use_container_width=True)

	with col6:
		# Base de calcul pour le KPI de refus: toutes les promesses réalisées,
		# avec ou sans désistement, filtrées par entité / direction / période.
		df_base = df_recrutement.copy() if df_recrutement is not None else pd.DataFrame()
		if not df_base.empty and isinstance(global_filters, dict):
			entite = global_filters.get("entite")
			direction = global_filters.get("direction")
			if entite and entite != "Toutes" and "Entité demandeuse" in df_base.columns:
				df_base = df_base[df_base["Entité demandeuse"] == entite]
			if (
				direction
				and direction != "Toutes"
				and "Direction concernée" in df_base.columns
			):
				df_base = df_base[df_base["Direction concernée"] == direction]

			# Filtre d'année:
			# - si Date de désistement existe, on prend son année
			# - sinon, on prend l'année de Date d'acceptation du candidat
			annee_sel = global_filters.get("periode_recrutement", "Toutes")
			if annee_sel != "Toutes" and not df_base.empty:
				annee = int(annee_sel)
				des_year = None
				acc_year = None
				if "Date de désistement" in df_base.columns:
						des_year = df_base["Date de désistement"].dt.year  # type: ignore[attr-defined]
				if "Date d'acceptation du candidat" in df_base.columns:
						acc_year = df_base["Date d'acceptation du candidat"].dt.year  # type: ignore[attr-defined]

				if des_year is not None and acc_year is not None:
					mask = (des_year.notna() & (des_year == annee)) | (
						des_year.isna() & acc_year.notna() & (acc_year == annee)
					)
				elif des_year is not None:
					mask = des_year.notna() & (des_year == annee)
				elif acc_year is not None:
					mask = acc_year.notna() & (acc_year == annee)
				else:
					mask = pd.Series(False, index=df_base.index)

				df_base = df_base[mask].copy()

		res = compute_promise_refusal_rate_row(df_base)
		taux_refus = res["rate"] if res["rate"] is not None else 0.0
		numer = res["numerator"]
		denom = res["denominator"]

		st.markdown(
			"<div style='font-family:Arial,sans-serif; font-size:18px; font-weight:700; "
			"color:#111111; text-align:left; margin:8px 0 4px 0;'>"
			"Taux de refus des promesses d'embauche (%)</div>",
			unsafe_allow_html=True,
		)
		fig_refus = go.Figure(
			go.Indicator(
				mode="gauge+number",
				value=round(taux_refus, 1),
				number={"suffix": " %"},
				gauge={
					"axis": {"range": [0, 100], "visible": True},
					"bar": {"color": "#d62728"},
				},
			)
		)
		fig_refus.update_layout(
			height=280, margin=dict(t=20, b=20, l=20, r=20)
		)
		st.plotly_chart(fig_refus, use_container_width=True)
		st.caption(
			f"Numérateur (refus): {numer} | Dénominateur (promesses réalisées): {denom}"
		)

	st.markdown("---")
	with st.expander(
		"🔍 Debug - Détails des lignes (base KPI promesses / refus)", expanded=False
	):
		try:
			st.markdown(
				"**Lignes de promesse d'embauche (avec ou sans désistement):**"
			)
			df_debug = df_base.copy() if "df_base" in locals() else df_filtered.copy()

			desist_col = "Date de désistement"
			if desist_col in df_debug.columns:
				df_debug[desist_col] = pd.to_datetime(
					df_debug[desist_col], errors="coerce"
				).dt.strftime("%d/%m/%Y")

			candidate_col = (
				"Nom Prénom du candidat retenu yant accepté la promesse d'embauche"
			)
			if candidate_col not in df_debug.columns:
				for c in df_debug.columns:
					if "candidat retenu" in c.lower() and "promesse" in c.lower():
						candidate_col = c
						break

			cols_debug = []
			if candidate_col in df_debug.columns:
				cols_debug.append(candidate_col)
			cols_debug.extend([
				"Poste demandé",
				"Colonne TG Hire",
			])
			if desist_col in df_debug.columns:
				cols_debug.append(desist_col)

			prom_col = res.get("columns", {}).get("prom") if isinstance(res, dict) else None
			refus_col = (
				res.get("columns", {}).get("refus") if isinstance(res, dict) else None
			)

			for extra_col in [prom_col, refus_col]:
				if (
					extra_col
					and extra_col in df_debug.columns
					and extra_col not in cols_debug
				):
					cols_debug.append(extra_col)

			if (
				prom_col
				and refus_col
				and prom_col in df_debug.columns
				and refus_col in df_debug.columns
			):
				prom_vals = pd.to_numeric(df_debug[prom_col], errors="coerce").fillna(0)
				refus_vals = pd.to_numeric(df_debug[refus_col], errors="coerce").fillna(0)
				df_debug["Contribue KPI Refus"] = prom_vals.eq(1) & refus_vals.eq(1)
				cols_debug.append("Contribue KPI Refus")

			cols_available = [c for c in cols_debug if c in df_debug.columns]
			if cols_available:
				st.dataframe(
					df_debug[cols_available].reset_index(drop=True),
					use_container_width=True,
					hide_index=True,
				)
			else:
				st.dataframe(
					df_debug.reset_index(drop=True),
					use_container_width=True,
					hide_index=True,
				)
		except Exception:
			st.write("Aucune donnée disponible pour le debug.")


def main():
	st.title("📊 Reporting RH - Recrutements clôturés")

	st.sidebar.markdown("### 🔧 Source de données")
	uploaded_excel = st.sidebar.file_uploader(
		"Fichier Excel de recrutement",
		type=["xlsx", "xls"],
		key="rrh_excel_upload",
	)

	_, df_recrutement = load_data_from_files(excel_file=uploaded_excel)

	if df_recrutement is None or df_recrutement.empty:
		st.error("Aucune donnée de recrutement disponible.")
		return

	st.sidebar.markdown("---")
	st.sidebar.subheader("Filtres globaux")
	global_filters = create_global_filters(df_recrutement)

	create_recrutements_clotures_tab(df_recrutement, global_filters)


if __name__ == "__main__":
	main()

