# a_linear_algebra_primer_for_financial_engineering

Section-level conversion checklist. Every page number below is a **1-based PDF
page index**, already offset-corrected (`PAGE_OFFSET=16`, so PDF index =
printed page + 16). Pass these numbers to subagents as-is — never re-apply the
offset.

- Source: `pdfs/baruch_01_textbook.pdf` (341 pages, no text layer)
- Copyright page: PDF page 4 — never typeset
- Figures: **none in this book.** Every float is a framed pseudocode `Table N.M`.
  `FIGURE_NUMBERING="two-part"` is recorded for the float caption scheme.
- Theorem-like environments use **separate** counters per type, reset per
  chapter (Definition 4.7 / Definition 4.8 share a page with Theorem 4.6;
  Theorem 5.1 is immediately followed by Lemma 5.1). Do not merge them.
- Exercises: plain arabic list restarting at 1 in each `N.M Exercises`
  section; sub-parts are `(i)`, `(ii)`, …

## Phase 0 — Setup

- [x] `book.conf` (verified with `bash -n`)
- [x] `latex/preamble.tex`
- [x] `latex/main.tex`
- [x] `latex/frontmatter.tex`
- [x] `latex/figures/placeholder.png`
- [x] Directory tree `latex/ch01`…`ch10`, `latex/figures/ch01`…`ch10`,
      `latex/backmatter`, `build/`

## Chapter 1 — Vectors and matrices (PDF 17–52)

- [x] 1.1 Column and row vectors. Column form and row form of a matrix.
- [x] 1.1.1 Covariance matrix computation from time series data
- [x] 1.2 Matrix rank, nullspace, and range of a matrix
- [x] 1.2.1 A one period market model
- [x] 1.3 Nonsingular matrices
- [x] 1.4 Diagonal matrices
- [x] 1.4.1 Converting between covariance and correlation matrices
- [x] 1.5 Lower triangular and upper triangular matrices. Tridiagonal matrices.
- [x] 1.6 References
- [x] 1.7 Exercises

## Chapter 2 — LU decomposition (PDF 53–102)

- [x] 2.1 The numerical solution of linear systems
- [x] 2.2 Forward substitution
- [x] 2.2.1 Finding discount factors using forward substitution
- [x] 2.3 Backward substitution
- [x] 2.4 LU decomposition without pivoting
- [x] 2.4.1 Pseudocode and operation count for LU decomposition
- [x] 2.5 Linear solvers using LU decomposition without pivoting
- [x] 2.5.1 LU linear solvers for tridiagonal matrices
- [x] 2.6 LU decomposition with row pivoting
- [x] 2.7 Linear solvers using LU decomposition with row pivoting
- [x] 2.7.1 Solving linear systems corresponding to the same matrix
- [x] 2.7.2 Finding discount factors using the LU decomposition
- [x] 2.8 Cubic spline interpolation
- [x] 2.8.1 Cubic spline interpolation for zero rate curves
- [x] 2.9 References
- [x] 2.10 Exercises

## Chapter 3 — The Arrow--Debreu one period market model (PDF 103–126)

- [x] 3.1 One period market models
- [x] 3.2 Arbitrage--free markets
- [x] 3.3 Complete markets
- [x] 3.4 Risk--neutral pricing in arb--free complete markets
- [x] 3.4.1 State prices
- [x] 3.5 A one period index options market model
- [x] 3.6 References
- [x] 3.7 Exercises

## Chapter 4 — Eigenvalues and eigenvectors (PDF 127–154)

- [x] 4.1 Definitions and properties
- [x] 4.2 Diagonal forms
- [x] 4.3 Diagonally dominant matrices
- [x] 4.4 Numerical computation of eigenvalues
- [x] 4.5 Eigenvalues and eigenvectors of tridiagonal symmetric matrices
- [x] 4.6 References
- [x] 4.7 Exercises

## Chapter 5 — Symmetric matrices and symmetric positive definite matrices (PDF 155–176)

- [x] 5.1 Symmetric matrices
- [x] 5.2 Symmetric positive definite matrices
- [x] 5.2.1 Sylvester's Criterion
- [x] 5.2.2 Positive definiteness criteria for symmetric matrices
- [x] 5.3 The diagonal form of symmetric matrices
- [x] 5.4 References
- [x] 5.5 Exercises

## Chapter 6 — Cholesky decomposition. Efficient cubic spline interpolation. (PDF 177–208)

- [x] 6.1 Cholesky decomposition
- [x] 6.1.1 Pseudocode and operation count for Cholesky decomposition
- [x] 6.2 Linear solvers for symmetric positive definite matrices
- [x] 6.2.1 Solving linear systems corresponding to the same spd matrix
- [x] 6.3 Optimal linear solvers for tridiagonal spd matrices
- [x] 6.4 Efficient implementation of the cubic spline interpolation
- [x] 6.4.1 Efficient cubic spline interpolation for zero rate curves
- [x] 6.5 References
- [x] 6.6 Exercises

## Chapter 7 — Covariance matrices. Multivariate normals. (PDF 209–242)

- [ ] 7.1 Covariance and correlation matrices
- [ ] 7.2 Covariance and correlation matrix estimation from time series data
- [ ] 7.3 Linear Transformation Property
- [ ] 7.4 Necessary and sufficient conditions for covariance and correlation matrices
- [ ] 7.5 Finding normal variables with a given covariance or correlation matrix
- [ ] 7.5.1 Monte Carlo simulation for basket options pricing
- [ ] 7.6 Multivariate normal random variables
- [ ] 7.7 Multivariate random variables formulation for covariance and correlation matrices
- [ ] 7.8 References
- [ ] 7.9 Exercises

## Chapter 8 — Ordinary least squares (OLS). Linear regression. (PDF 243–266)

- [ ] 8.1 Ordinary least squares
- [ ] 8.1.1 Least squares for implied volatility computation
- [ ] 8.2 Linear regression: ordinary least squares for time series data
- [ ] 8.3 Ordinary least squares for random variables
- [ ] 8.4 The intuition behind ordinary least squares for time series data
- [ ] 8.5 References
- [ ] 8.6 Exercises

## Chapter 9 — Efficient portfolios. Value at Risk. (PDF 267–302)

- [ ] 9.1 Efficient portfolios. Markowitz portfolio theory.
- [ ] 9.2 Blueprints for finding efficient portfolios
- [ ] 9.3 Minimum variance portfolios
- [ ] 9.3.1 Minimum variance portfolios and the tangency portfolio
- [ ] 9.4 Maximum return portfolios
- [ ] 9.4.1 Maximum return portfolios and the tangency portfolio
- [ ] 9.5 Minimum variance portfolio with no cash position
- [ ] 9.6 Value at Risk (VaR). Portfolio VaR.
- [ ] 9.6.1 VaR of combined portfolios and subadditivity
- [ ] 9.7 References
- [ ] 9.8 Exercises

## Chapter 10 — Mathematical appendix and technical results (PDF 303–334)

- [ ] 10.1 Numerical linear algebra tools
- [ ] 10.1.1 Determinants
- [ ] 10.1.2 Permutation matrices
- [ ] 10.1.3 Orthogonality
- [ ] 10.1.4 Quadratic forms
- [ ] 10.2 Mathematical tools
- [ ] 10.2.1 Multivariable functions
- [ ] 10.2.2 Lagrange multipliers
- [ ] 10.2.3 The "Big O" notation
- [ ] 10.3 European options overview
- [ ] 10.4 Eigenvalues of symmetric matrices
- [ ] 10.5 Row rank equal to column rank
- [ ] 10.6 Technical results for the Cholesky and LU decompositions
- [ ] 10.7 More technical results
- [ ] 10.8 Exercises

## Back matter (PDF 335–341)

- [ ] Bibliography (PDF 335–337) — numeric `\bibitem` keys, cited as `[13]`
- [ ] Index (PDF 338–341)

## Optional front matter (outside every CHNN_PAGES range)

Not covered by any chapter range; convert only if the user asks.

- [ ] Preface (PDF 13)
- [ ] Acknowledgments (PDF 15)

## Failed chunks

_(none yet)_

## Unresolved compile errors

_(none yet)_
