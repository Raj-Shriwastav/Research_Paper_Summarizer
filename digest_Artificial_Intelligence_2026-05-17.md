# 📚 Research Digest: Artificial Intelligence
**Date:** 2026-05-17  |  **Papers summarized:** 2

---

# 📄 Learning quantum Hamiltonians at any temperature in polynomial time
**Authors:** Ainesh Bakshi, Allen Liu, Ankur Moitra, Ewin Tang
**Paper:** [https://arxiv.org/abs/2310.02243](https://arxiv.org/abs/2310.02243)

---

### Novel Idea/Solution: Main Contribution  

**Paper:** *Learning quantum Hamiltonians at any temperature in polynomial time*  
**Authors:** Ainesh Bakshi, Allen Liu, Ankur Moitra, Ewin Tang  

---

## A. What the author found (The Issue)

### 1. The problem: Hamiltonian learning from thermal states  
In many‑body quantum physics a **Hamiltonian** \(H\) encodes all the interaction strengths (the “knobs”) of a system of \(n\) qubits arranged on a lattice.  Experimentally we can often **prepare the Gibbs (thermal) state**  

\[
\rho_\beta \;=\; \frac{e^{-\beta H}}{\operatorname{Tr}\!\big(e^{-\beta H}\big)},
\]

where \(\beta>0\) is the (known) inverse temperature.  The **Hamiltonian‑learning task** asks: *given many independent copies of \(\rho_\beta\), can we recover the unknown real coefficients \(\{\lambda_a\}\) that weight a known set of local Pauli terms \(\{E_a\}\) in*

\[
H \;=\; \sum_{a=1}^{m} \lambda_a E_a,\qquad | \lambda_a | \le 1,
\]

to within additive error \(\varepsilon\) for every \(a\)?

This is a central sub‑routine for **characterising, verifying, and controlling** quantum devices (analog quantum simulators, quantum annealers, etc.).  Knowing the Hamiltonian lets scientists confirm that a device really implements the model they intended (e.g., the Fermi–Hubbard model) and diagnose why it may be deviating.

### 2. Prior state of the art  

| Work | Temperature regime | Runtime | Sample complexity |
|------|-------------------|---------|-------------------|
| **AAKS20** (Anshu, Arunachalam, Kuwahara, Soleimanifar, 2020) | *any* constant \(\beta\) | **Exponential** in \(n\) (though polynomial in \(1/\varepsilon\) and \(\beta\)) | **Polynomial** in \(n,1/\varepsilon,\beta\) |
| **HKT22** (Haah, Kothari, Tang, 2022) | **High‑temperature** (small \(\beta\)) | Polynomial | Polynomial |
| **AAKS21** (Anshu et al., 2021) | **Commuting** Hamiltonians (all \(E_a\) commute) | Polynomial | Polynomial |
| **Other works** (e.g., BAL19, Bairey‑Arad‑Lindner 2019) | Various special cases, often heuristic or with super‑polynomial overhead | – | – |

Thus, **the open problem** (highlighted in surveys such as [AA23] and [Alh23]) was:

> **Can we learn a *general* local Hamiltonian at *any* (constant) temperature using only polynomial time and a polynomial number of Gibbs‑state copies?**

The difficulty stems from the fact that the map \(\lambda \mapsto \rho_\beta\) is **highly non‑linear** (it involves the matrix exponential) and the exponential’s Taylor series would require degree \(\Theta(n)\) to capture the spectrum accurately, seemingly forcing exponential computation.

### 3. Why this matters  

* **Scientific impact:** Enables systematic, scalable verification of analog quantum simulators operating at low temperature, where interesting phases (topological order, superconductivity) appear.  
* **Algorithmic significance:** Provides the first *computationally efficient* algorithm for a fundamental learning problem that sits at the intersection of quantum many‑body physics, statistical learning, and computational complexity.  
* **Methodological breakthrough:** Introduces a new way to **approximate the exponential function with a “flat” low‑degree polynomial**, opening a toolbox that may be useful for other quantum‑algorithmic tasks (e.g., ground‑state preparation, quantum Monte‑Carlo).

---

## B. How they tackled it (The Solution)

The authors’ contribution is a **three‑layer pipeline** that converts the non‑linear learning problem into a tractable low‑degree polynomial system, then solves it with a **low‑degree Sum‑of‑Squares (SOS) relaxation**.  The key technical ingredients are:

### 1. Flat polynomial approximation to the exponential  

* **Goal:** Approximate the scalar function \(f(x)=e^{-\beta x}\) on the interval \([-1,1]\) (the possible eigenvalues of a normalized Hamiltonian) **with a polynomial \(p_d(x)\) of degree \(d = \operatorname{poly}(\beta,1/\varepsilon)\)** such that  

  \[
  \big|p_d(x) - e^{-\beta x}\big| \le \varepsilon \quad\text{for all } x\in[-1,1],
  \]
  **and** the polynomial is *flat* near the origin: its derivatives up to order \(k\) (the locality of each term) are tiny.  

* **Construction:** The authors start from the Chebyshev expansion of \(e^{-\beta x}\) and apply a **filtering technique** (similar to Jackson’s theorem) that damps high‑frequency components while preserving low‑order moments.  The result is a **“flat” polynomial** whose coefficients decay rapidly, allowing the degree to stay polynomial in the relevant parameters.  

* **Why flatness matters:** When we later replace the matrix exponential \(e^{-\beta H}\) by \(p_d(H)\), the **nested commutators** that appear (see next step) involve derivatives of the polynomial.  Flatness guarantees that commutators of order up to the locality \(k\) are **extremely small**, which in turn yields **low‑degree polynomial equations** for the unknown coefficients \(\lambda_a\).

### 2. Translating the exponential into nested commutators  

* **Key identity:** For any analytic function \(f\),

  \[
  f(H) = f\!\big(\sum_a \lambda_a E_a\big) = \sum_{r=0}^{\infty} \frac{1}{r!}\,\underbrace{[H,[H,\dots,[H}_{r\text{ times}},\,\cdot\,]\dots]],
  \]

  where \([A,B]=AB-BA\) is the commutator.  When \(f\) is replaced by the flat polynomial \(p_d\), the series truncates at degree \(d\).  

* **Locality exploitation:** Each Pauli term \(E_a\) acts on at most \(k\) qubits.  Because commutators of **disjoint** local terms vanish, any nested commutator of depth larger than \(k\) automatically becomes zero or exponentially suppressed (thanks to the flatness).  Consequently, the **effective degree** of the polynomial system that relates observable expectations to the \(\lambda_a\) is **\(O(kd)\)**, still polynomial.

* **Observable equations:** For any local Pauli observable \(O\) (e.g., a single‑site \(Z\) operator), the expectation under the Gibbs state is  

  \[
  \langle O\rangle_{\rho_\beta}
  \;=\;
  \operatorname{Tr}\!\big(O\,\rho_\beta\big)
  \;\approx\;
  \frac{\operatorname{Tr}\!\big(O\,p_d(H)\big)}{\operatorname{Tr}\!\big(p_d(H)\big)}.
  \]

  Both numerator and denominator are **multivariate polynomials** in the unknowns \(\{\lambda_a\}\).  By measuring a **polynomially‑many** carefully chosen local observables (e.g., all single‑site Pauli strings and a few two‑site strings), we obtain a **system of polynomial equations** whose solution yields the \(\lambda_a\).

### 3. Solving the polynomial system via a low‑degree SOS relaxation  

* **Sum‑of‑Squares hierarchy:** Given a set of polynomial constraints \(\{g_i(\lambda)=0\}\), the SOS method searches for a **pseudo‑distribution** over the variables that satisfies all constraints up to a certain degree \(D\).  If such a pseudo‑distribution exists, a **semidefinite program (SDP)** of size \(n^{O(D)}\) can be solved in polynomial time (provided \(D\) is constant or grows slowly).

* **Why low degree suffices:**  
  * The flat polynomial guarantees that the **error terms** (differences between the true exponential and its polynomial surrogate) are of order \(\varepsilon\).  
  * The **locality** of the Hamiltonian ensures that each constraint involves at most \(k\) variables, so a **degree‑\(2k\)** SOS relaxation already captures all necessary moment information.  
  * The authors prove a **robustness lemma**: if a pseudo‑distribution satisfies the polynomial constraints within additive error \(\varepsilon\), then the extracted moments are within \(O(\varepsilon)\) of the true coefficients.  

* **Algorithmic steps:**  

  1. **Sample collection:** Prepare \(N = \operatorname{poly}(n,1/\varepsilon,\beta)\) copies of \(\rho_\beta\).  For each copy, measure a randomly chosen local Pauli observable from a pre‑specified set \(\mathcal{O}\).  Estimate the expectation values \(\widehat{\mu}_O\) to additive error \(\varepsilon/10\) using standard concentration (Hoeffding’s inequality).  

  2. **Polynomial construction:** For each observable \(O\in\mathcal{O}\), write the **approximate expectation equation**  

     \[
     \widehat{\mu}_O \;=\; \frac{P_O(\lambda)}{Q(\lambda)} \;+\; \delta_O,
     \]

     where \(P_O,Q\) are explicit low‑degree polynomials derived from \(p_d\) and \(\delta_O\) is the statistical error.  

  3. **SOS formulation:** Introduce a **moment matrix** \(M\) indexed by monomials of degree up to \(D = O(kd)\).  Impose linear constraints on the entries of \(M\) that encode the polynomial equations (cross‑multiplying denominators to obtain homogeneous constraints).  Add the **positive‑semidefinite** constraint \(M \succeq 0\).  

  4. **SDP solve:** Run a standard interior‑point SDP solver (e.g., MOSEK, SDPA) to obtain a feasible moment matrix.  Because \(D\) is polynomial, the SDP size is \(\operatorname{poly}(n,1/\varepsilon,\beta)\) and runs in polynomial time.  

  5. **Extraction:** Recover the coefficients \(\{\lambda_a\}\) from the first‑order moments of the pseudo‑distribution (the entries of \(M\) corresponding to monomials \(\lambda_a\)).  A rounding step (simple thresholding) yields \(\tilde\lambda_a\) satisfying \(|\tilde\lambda_a-\lambda_a|\le\varepsilon\) with high probability.  

* **Complexity guarantees:**  

  * **Sample complexity:** \(N = \widetilde{O}\!\big(n^{c_1}\, \beta^{c_2}\, \varepsilon^{-c_3}\big)\) for absolute constants \(c_i\).  The tilde hides polylog factors.  
  * **Runtime:** \(\widetilde{O}\!\big(n^{c_4}\, \beta^{c_5}\, \varepsilon^{-c_6}\big)\) – polynomial in all parameters, **independent of the system size exponent** that plagued AAKS20.  

* **Theoretical proof sketch:**  

  1. **Approximation error bound** for the flat polynomial (Section 3.1 of the paper).  
  2. **Locality‑induced sparsity** of the commutator expansion (Lemma 3.4).  
  3. **Soundness of the SOS relaxation**: any true Hamiltonian yields a feasible moment matrix; conversely, any feasible

---

### 📝 Combined Summary
The paper is about learning quantum Hamiltonians at any temperature in polynomial time. The problem is that prior methods either had exponential runtime or were limited to high temperatures or commuting Hamiltonians. The authors' solution involves approximating the exponential function with a flat polynomial, translating the problem into polynomial equations using commutators, and solving it with a low-degree SOS relaxation.

For the Combined Summary, I need to weave together the problem, prior work, their approach, and the significance. I should mention the three-layer pipeline: flat polynomial approximation, translating to commutators, and SOS relaxation. Also, highlight the polynomial time and sample complexity, and the impact on quantum verification and algorithm design.

The

### ⭐ Key Takeaway — MAKE NOTE OF THIS
The paper is about learning quantum Hamiltonians at any temperature in polynomial time. The problem is that prior methods either had exponential runtime or were limited to high temperatures or commuting Hamiltonians. The authors' solution involves approximating the exponential function with a flat polynomial, translating the problem into polynomial equations using commutators, and solving it with a low-degree SOS relaxation.

For the Combined Summary, I need to weave together the problem, prior work, their approach, and the significance. I should mention the three-layer pipeline: flat polynomial approximation, translating to commutators, and SOS relaxation. Also, highlight the polynomial time and sample complexity, and the impact on quantum verification and algorithm design.

The Key Takeaway needs to be punchy. The main takeaway is the flat polynomial approximation allowing efficient learning at any temperature. Emphasize that this solves a long-standing problem and opens new possibilities for quantum devices.

I need to make sure the summary is cohesive, connects all parts, and the takeaway is impactful. Avoid jargon where possible but maintain technical accuracy. Check that the links are included correctly. Also, ensure the sections are engaging and concise.
</think>

### 📝 Combined Summary  
The paper *Learning quantum Hamiltonians at any temperature in polynomial time* addresses a critical challenge in quantum many-body physics: reconstructing the interaction parameters (Hamiltonian coefficients) of a system from its thermal state at any fixed temperature. Prior methods either required exponential time for general Hamiltonians or were restricted to high-temperature or commuting systems. The authors introduce a groundbreaking three-step solution. First, they approximate the non-linear Gibbs state exponential $ e^{-\beta H} $ with a *flat low-degree polynomial*, ensuring rapid coefficient decay and suppressing higher-order commutator terms. Second, they translate this approximation into a system of polynomial equations by leveraging the locality of Hamiltonian terms and the structure of nested commutators, reducing the problem to a low-degree representation. Finally, they solve this system using a low-degree Sum-of-Squares (SOS) relaxation, which guarantees efficient recovery of the Hamiltonian coefficients with polynomial runtime and sample complexity. This approach bridges the gap between theoretical learning and practical quantum verification, enabling scalable characterization of analog quantum simulators at arbitrary temperatures—a feat previously deemed intractable due to the exponential complexity of thermal states.

---

### ⭐ Key Takeaway — MAKE NOTE OF THIS  
The most impactful innovation is the *flat polynomial approximation* of the exponential function, which tames the exponential’s non-linearity into a tractable low-degree form. By ensuring the polynomial’s derivatives vanish rapidly (via Chebyshev filtering), the authors sidestep the exponential’s spectral complexity, transforming Hamiltonian learning into a polynomial system solvable in polynomial time. This breakthrough not only resolves a decade-old open problem but also provides a toolkit for future quantum algorithms, from ground-state preparation to error correction. For researchers, this means robust verification of quantum devices at low temperatures—where exotic phases of matter emerge—without exponential overhead. For the field, it marks a shift toward algorithmic methods that harmonize with the inherent locality of physical systems. **This is the first polynomial-time algorithm for Hamiltonian learning at any temperature, and it redefines what’s possible in quantum characterization.

### 🔗 Useful Links
- 📄 **Original Paper**: https://arxiv.org/abs/2310.02243


---

# 📄 Active teacher selection for reward learning
**Authors:** Rachel Freedman, Justin Svegliato, Kyle Wray, Stuart Russell
**Paper:** [https://arxiv.org/abs/2310.15288](https://arxiv.org/abs/2310.15288)

---

### Novel Idea/Solution: Main Contribution

#### A. What the author found (The Issue)
The core issue identified by the authors is a fundamental mismatch between how we currently train AI systems and the reality of how human feedback is collected. Most modern machine learning systems—particularly those using Reinforcement Learning from Human Feedback (RLHF)—rely on a **"single-teacher assumption."** This means they treat all human feedback as if it were generated by a single, consistent, and equally reliable entity.

In practice, this is rarely true. AI developers aggregate feedback from a diverse, heterogeneous pool of humans, including crowdworkers, domain experts, and researchers. These individuals vary significantly in their expertise, attentiveness, and decision-making capabilities. The authors point out that even in current state-of-the-art systems, annotators and researchers disagree with one another 23% to 37% of the time.

This "unrecognized heterogeneity" is problematic for several reasons:
*   **Distorted Reward Functions:** When an AI assumes all teachers are equally rational, it fails to account for the fact that some teachers are more prone to error than others. This leads to a "noisy" or inaccurate understanding of what the human actually wants, causing the model to learn a flawed objective function.
*   **Inefficiency:** In safety-critical or high-stakes environments, expert time is expensive and scarce. Current systems lack a framework to decide *which* teacher to query and *when* to query them. They treat all feedback as equal, failing to weigh the cost of a high-quality expert against the lower cost (and lower reliability) of a generalist.
*   **Fragility:** Prior research has shown that reward learning is highly sensitive to incorrect assumptions about feedback generation. If the model assumes a single, perfect teacher but receives input from a noisy, diverse crowd, the resulting AI behavior can become degenerate or "hack" the reward function.

Before this work, there was no formal framework to model these differences between teachers or to make strategic, cost-aware decisions about which teacher to consult.

#### B. How they tackled it (The Solution)
The authors introduced the **Hidden Utility Bandit (HUB)** framework, a novel way to formalize reward learning as a sequential decision-making problem involving multiple teachers with varying levels of reliability and cost.

**1. The HUB Framework:**
The HUB framework treats the reward learning process as a partially-observable problem. The agent (the AI) interacts with:
*   **Items ($I$):** The things being evaluated (e.g., pieces of content).
*   **Arms ($K$):** Distributions over items (e.g., different sources of content).
*   **Teachers:** Individuals with distinct **rationality parameters ($\beta$)** and **query costs ($F$)**.

**2. Modeling Rationality:**
The authors utilize the **Boltzmann-rationality model**. In this model, the probability that a teacher prefers item $i$ over $j$ is determined by the difference in their utilities, scaled by the teacher's rationality parameter $\beta$. A higher $\beta$ indicates a more expert, reliable teacher who is less likely to make mistakes on "hard" comparisons (where the utility difference is small).

**3. Active Teacher Selection (ATS):**
The primary contribution is the development of an **Active Teacher Selection (ATS)** algorithm. Unlike previous approaches that were either "myopic" (only looking at the immediate next step) or assumed a fixed distribution of teachers, the ATS algorithm:
*   **Interleaves Inference and Action:** It treats the process as an online, sequential task. The agent must decide between "exploring" (querying a teacher to learn the reward function) and "exploiting" (pulling an arm to gain utility).
*   **Cost-Aware Planning:** The algorithm plans multiple steps ahead, weighing the expected "information gain" from a specific teacher against the financial or time cost of that query.
*   **Inference of $\beta$:** Recognizing that $\beta$ is rarely known in advance, the authors provide a method to infer a teacher's rationality parameter ($\hat{\beta}$) dynamically as the system collects more data.

**4. Key Innovations:**
*   **Individual Modeling:** Unlike previous work that modeled teachers as a "distribution" or "population," the HUB framework models them as individuals, allowing the agent to learn who is good at what and select them accordingly.
*   **Multi-Step Lookahead:** By moving beyond simple greedy heuristics, the agent can decide when it is worth paying for an expert versus when a cheaper, less-reliable teacher is sufficient to resolve uncertainty.

#### C. Explain Like I'm 10 (ELI10)
Imagine you are trying to learn which flavor of ice cream is the best, but you aren't allowed to taste them yourself. Instead, you have to ask a group of friends. 

Some of your friends are "Ice Cream Experts"—they have a very refined palate and almost always know which flavor is better. However, they are very busy and charge you $5 every time you ask them a question. Other friends are just random people at the park. They are free to talk to, but they make mistakes a lot, especially if the two flavors are very similar.

If you just ask everyone randomly, you might waste all your money on the experts when you didn't need to, or you might get bad advice from the random people and end up with a flavor you hate. 

The "Hidden Utility Bandit" is like a smart robot assistant that helps you decide: "Is this question hard enough that I should pay the $5 for the expert, or is it easy enough that I can just ask the free person?" It keeps track of who is reliable, how much money you have left, and how much you need to know to make the right choice. It helps you get the best ice cream while spending your money as wisely as possible!

#### C2. Explain for a College Student
The HUB framework addresses the **Reward Misspecification** problem by reframing reward learning as a **Partially Observable Markov Decision Process (POMDP)**. 

In standard RLHF, we assume a single, static teacher model. The authors relax this by introducing a set of teachers $\{T_1, T_2, ..., T_n\}$, where each teacher $T_n$ is characterized by a tuple $(\beta_n, F_n)$—representing their Boltzmann rationality and their associated query cost. 

The **Boltzmann-rationality model** is defined as:
$$Pr(i \succ j) = \frac{e^{\beta U(i)}}{e^{\beta U(i)} + e^{\beta U(j)}}$$
This captures the empirical reality that human error is inversely proportional to the utility gap between two items. 

The **ATS algorithm** functions as an agent that must solve a dual-objective optimization problem:
1.  **Information Gain:** Reducing the entropy of the belief distribution over the true utility function $U$.
2.  **Cumulative Reward:** Maximizing the expected utility of the arms pulled.

By using a multi-step lookahead, the agent performs **Active Learning** in a cost-constrained environment. It essentially performs a cost-benefit analysis at each timestep: is the expected reduction in uncertainty (and the subsequent increase in future reward) worth the immediate cost $F_n$ of querying teacher $T_n$? This shifts the paradigm from passive data collection to **strategic, resource-aware information acquisition**, which is critical for scaling AI alignment in real-world, heterogeneous data environments. 

For further reading on the foundations of these concepts, you can explore:
*   [Reinforcement Learning from Human Feedback (RLHF)](https://openai.com/blog/instruction-following/)
*   [Multi-Armed Bandits (MAB)](https://en.wikipedia.org/wiki/Multi-armed_bandit)
*   [Boltzmann-Rationality in Decision Making](https://arxiv.org/abs/1406.1880)

---

### 📝 Combined Summary
Current AI alignment techniques, particularly Reinforcement Learning from Human Feedback (RLHF), typically rely on a "single-teacher assumption," treating all human feedback as if it came from one consistent, reliable source. In reality, feedback is gathered from a heterogeneous pool of annotators with varying levels of expertise and reliability, leading to distorted reward functions and the inefficient use of expensive expert time. To solve this, the authors introduce the **Hidden Utility Bandit (HUB)** framework, which reframes reward learning as a sequential decision-making problem. By utilizing a Boltzmann-rationality model, the framework assigns individual rationality parameters ($\beta$) and query costs ($F$) to different teachers. This enables the **Active Teacher Selection (ATS)** algorithm to strategically decide whether to query a cheap but noisy generalist or an expensive but precise expert. By interleaving inference with a multi-step lookahead, the system optimizes the trade-off between the cost of information and the gain in reward accuracy, transforming reward learning from a passive data-collection exercise into a strategic, resource-aware optimization process.

### ⭐

### ⭐ Key Takeaway — MAKE NOTE OF THIS
The most impactful contribution of this paper is the shift from **aggregate feedback to strategic teacher selection.** Instead of treating human noise as a statistical nuisance to be averaged out, the authors treat teacher reliability as a latent variable to be modeled and optimized. This is a game-changer for AI alignment because expert human time is the most expensive and scarcest resource in the loop. By treating "who to ask" as a cost-benefit optimization problem, the HUB framework provides a blueprint for building AI systems that can autonomously navigate the tension between budget constraints and the need for high-precision safety guarantees. If you are scaling RLHF, stop treating your annotators as a monolith; start treating them as a portfolio of assets with different costs and accuracies.

### 🔗

### 🔗 Useful Links
- 📄 **Original Paper**: https://arxiv.org/abs/2310.15288
