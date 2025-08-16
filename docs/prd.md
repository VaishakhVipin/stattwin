# ⚽ StatTwin

*Find your player's statistical twin.*

---

## 🎯 Overview

StatTwin is a machine learning–powered web app that allows users to select a player (past or present), apply filters (age, league, continent, season), and find the most statistically similar players.

This project is designed as a **pre–deep learning ML stack** — focusing on similarity, clustering, and data wrangling instead of neural networks. It builds strong intuition around handling real-world sports data and preparing it for ML.

---

## 🛠️ Tech Stack

### Backend

* **Python** → main language
* **FastAPI** → backend API framework
* **pandas** → data wrangling
* **numpy** → vector ops
* **scikit-learn** → similarity, clustering, PCA/t-SNE
* **uvicorn** → dev server

### Frontend

* **Vite + React** → modern frontend framework
* **Tailwind / shadcn** → styling (optional)
* **Plotly / D3.js** → interactive visualizations

---

## 📂 Data

* Use **FBRef soccer stats** via API (fbrapi.com) or CSV exports.
* Dataset includes per 90 stats, passing, shooting, defending, possession, etc.
* Enrich with metadata: player age, position, league, continent, season.

---

## 🔄 Workflow

1. **Player Selection**

   * User searches + selects a player.
   * Backend retrieves that player’s stat vector.

2. **Filters (Optional)**

   * User applies filters: age, league, continent, season, position.
   * Backend narrows candidate pool with pandas masks.

3. **Similarity Engine** (possible approaches)

   * **Z-score normalization**: normalize stats across dataset (per 90 basis).
   * **Cosine similarity**: measure angle between vectors for playstyle similarity.
   * **Euclidean distance**: measure overall distance between stat profiles.
   * **Weighted similarity**: allow weighting certain stat categories (passing > shooting, etc.) based on desired player position.
   * **Dimensionality reduction (PCA)**: project to fewer dimensions to reduce noise, then run similarity.

4. **Clustering & Visualization (optional MVP+1)**

   * Apply **K-Means** or **DBSCAN** to group players into archetypes.
   * Reduce dimensions with **PCA / t-SNE** for a 2D scatterplot map.

5. **Results**

   * FastAPI returns a JSON response with top N similar players + scores.
   * Frontend renders as interactive cards + optional scatterplot.

---

## ✅ Application structure

1. **Landing Page**

   * Search/select a reference player.

2. **Filter Panel**

   * Dropdowns/sliders for age, league, continent, season.

3. **Results Page**

   * Display list of top similar players with similarity scores.
   * Optionally render 2D scatterplot with PCA/t-SNE.

---

## 🌟 Future Extensions

* Historical comparisons across eras.
* Career trajectory prediction (regression).
* Support for multiple sports.
* Natural language query → filter mapping.
* Streamlit “playground” version for data exploration.

---

## 🔥 Why This Project

* Builds intuition with **data wrangling + feature engineering.**
* Forces you to deal with **normalization, similarity, and clustering**.
* Prepares you for deep learning by mastering the fundamentals of vector space reasoning.
* Fun + shareable: every sports fan wants to know who their favorite player’s “twin” is.

---
