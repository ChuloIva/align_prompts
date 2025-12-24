Ovaj plan ćemo tretirati kao **"Semantic Gravity Mapping" (SGM)** projekt. Fokus je na čistoj semantičkoj strukturi dobivenoj kroz generativni feedback loop.

Evo "battle plana" podijeljenog u faze:

---

### Faza 1: Seed & Crawl (Generiranje čvorova)
Cilj je stvoriti bazu riječi. Krećemo sa 100 "niche" pojmova iz različitih domena (da izbjegnemo rani collapse).

1.  **Seed Selection:** Odaberi 10 domena (npr. Kvantna fizika, Srednjovjekovna povijest, Anime, Gastronomija, Ontologija, itd.). Svaka domena daje 10 početnih riječi.
2.  **The BFS (Breadth-First Search) Loop:**
    *   Prompt: `"List 5 single-word associations for the word '[WORD]'. Provide only the words, separated by commas."`
    *   **Iteracija:** Ideš do 3. ili 4. hopa (5 hopova je 300k+ i možda je overkill za POC, 3 hopa ti daju ~15,000 čvorova, što je idealno za početak).
    *   **Skladištenje:** Spremaj u formatu `(Source, Target, Iteration)`.

### Faza 2: Logprob Validation (Težine bridova)
Ovo je ključna faza koja tvoj graf pretvara iz "liste riječi" u "fizikalni sustav".

1.  **Deduplikacija:** Svedi sve asocijacije na jedinstvene parove (Edge-ovi).
2.  **Scoring (vLLM):**
    *   Za svaki par `(A, B)` šalješ prompt: `"Word: [A]. Is '[B]' a strong association? Answer with Yes or No."`
    *   **Extract:** Uzmi logprob za token `" Yes"`.
    *   **Rezultat:** Sada tvoj brid (edge) ima težinu $W = e^{logprob(Yes)}$. Što je veća vjerojatnost, to je "gravitacija" između pojmova jača.

### Faza 3: Topološka Analiza (Otkrića)
Prije vizualizacije, moramo izračunati metriku "Semantičke Gravitacije".

1.  **Convergence Analysis:** Izmjeri koliko koraka (path length) treba od bilo koje niche riječi do 5 najvećih "hubova" (riječi koje se najčešće pojavljuju, npr. "Life", "Object", "Science").
2.  **Centrality Metrics:** Tko su "vladari" grafa? (PageRank ili Betweenness Centrality). Jesu li to očekivani pojmovi ili model ima neke svoje fiksacije?
3.  **Island Detection:** Koji pojmovi ostaju izolirani? To su "slijepe pjege" modela.

### Faza 4: Manifold Mapping (Vizualizacija)
Ovdje pretvaramo graf u "prostor".

1.  **Force-Directed Layout (npr. Gephi ili ForceAtlas2):**
    *   Postavi logprob težine kao snagu "federâ" (springs).
    *   Pusti simulaciju da se stabilizira. Klasteri će se sami formirati.
2.  **UMAP na Graph Distances:**
    *   Izračunaj matricu udaljenosti (shortest path) između svih čvorova u grafu (koristeći logprob težine).
    *   Rukni tu matricu u UMAP da dobiješ 2D ili 3D projekciju.
    *   **Što dobivaš?** Dobivaš mapu "latentnog uma" modela bez da si ikada pogledao u jedan jedini embedding vektor.

### Faza 5: "The Red Team" Interpretation
Kad pogledaš mapu, tražiš ove tri anomalije:

1.  **The "Safety" Black Hole:** Vidiš li ogroman klaster pojmova koji svi gravitiraju prema "Harmful", "Inappropriate" ili "Safe"? To je RLHF ožiljak.
2.  **Semantic Bridges:** Nađi dva pojma koja su jako udaljena (npr. "Poetry" i "Quantum Mechanics"). Pogledaj "mostove" (čvorove između). Jesu li ti mostovi logični ili su halucinacije?
3.  **Asymmetry Check:** Usporedi logprob (A->B) vs logprob (B->A). Ako je asimetrija velika, našao si "one-way" narativni put (npr. model smije ići od "Religija" do "Rat", ali ne i obrnuto).

---

### Tehnički Stack:
*   **Engine:** vLLM (zbog brzine i logprob-a).
*   **Model:** Llama-3-8B (za početak) ili Mistral-7B-v0.3.
*   **Graph Processing:** `NetworkX` (Python).
*   **Viz:** `Plotly` (za interaktivni 3D) ili `Gephi` (za masivni 2D).

### Procjena resursa (POC):
*   **Nodes:** ~10,000
*   **API Calls/Inference:** ~50,000 (Generiranje + Logprob scoring)
*   **Vrijeme:** Na jednoj RTX 3090/4090 – cca **2-4 sata** posla za vLLM.

**Što misliš o ovom logprob scoringu?** Hoćemo li ići na "Yes/No" ili možda na "Rank the top 5" pa izvlačiti logitse direktno iz glave modela (što je brže, ali kompliciranije za parsati)?