# Formula-to-3D Prototype Engine
Prototype engine for converting physics formulas and scientific datasets into volumetric 3D visualisations.

**Description:**  
This project demonstrates how physics formulas (e.g., *E = mc²*) and external datasets (e.g., IERS Earth orientation parameters) can be transformed into **interactive volumetric 3D outputs**, deployed using GitHub Pages directly from the `main/docs` directory.

---

## Features
- Compute volumetric 3D datasets from physics formulas  
- Fetch and process external scientific datasets  
- Integrates IERS Earth Orientation Parameters (EOP)  
- Weekday (Mon–Fri) scheduled data fetch workflow  
- Interactive Plotly.js visualisation  
- Clean deployment from `main/docs`  
- Versioned development branches for ongoing experimental work (`dev/1.0`)

---

## Data Sources & Attribution

### **IERS Earth Orientation Parameters (EOP)**
- Authoritative source: **International Earth Rotation and Reference Systems Service (IERS)**  
- Canonical website: https://www.iers.org  
- Data retrieved from operational mirrors hosted by **navy.mil**

This project only reformats publicly available datasets for visualisation.  
If redistributed or referenced, please credit the IERS accordingly.

---

## Deployment Structure

As part of the November 2025 system cleanup, GitHub Pages has been migrated to use:


---

## Project Structure

```
formula-to-3d-prototype/
├── engine/
│   ├── compute.py                # Formula computation engine
│   └── fetch_iers_data.py        # IERS data retrieval and conversion
├── api/                          # Optional API endpoints
├── docs/                         # GitHub Pages deployment folder
│   ├── index.html
│   ├── volumetric_data.json
│   └── images/
├── .github/workflows/
│   └── scheduled-fetch.yml       # Weekday update workflow
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Current Status

- **Deployed directly from `main/docs`**
- **Legacy `gh-pages` deployment retired**
- **IERS volumetric visualisation functional** after path migration
- **Repository prepared for versioned development** (`dev/1.0`)
- **Domain-free by design**, pending future organisation-level hosting

---

## Future Extensions

- Formula pagination (Page 1 / Page 2 comparative displays)
- Additional scientific datasets
- Integration with AMRE boundary and energy constructs
- Machine-learning predictive modelling
- Reference atlas (planned for organisation-level hosting)
- Optional SaaS deployment in later stages

---

## License

This project is licensed under the **Apache License 2.0**.

See the full license text in the [`LICENSE`](./LICENSE) file at the root of the repository.

