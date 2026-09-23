# AI Log
Capturing points during the conversation where Claude was pushed to really think about it's proposals and how the problem is sliced and diced.

### A. Scoping and understanding the problem
1. The fact that there are negative prices, is that intentional? Claude clarifies this a real-life scenario and negative prices exist in the market for various reasons, cannot simply zero out and then optimise, that would be dodging the problem. Relaxing the "cannot charge/discharge at same time" constraint with price forecast data that has negative prices can cause the solver to land on unrealistic profit numbers, this is a well documented and studied area in academia.

2. Explored free and open source solvers, ensured that negative numbers in the inputs would not break any of them and solvers in contention for use can work with such inputs.





### B. Solution Options
Claude made some crude assumptions that had to be challenged.

#### B.1 Hybrid (simple LP + binaries at negative price sequences)
1. Claude leaned on academic research that suggested in a single-market style problem, a simple LP without the charge/discharge constraint could still land on a valid/real answer, which isn't relevant here since we're dealing with a two-market problem. 
2. In a two-market problem, the battery would simply be used as a medium to charge/discharge at the same time if the spread in prices was big enough to cover the cycle inefficiency. 


#### B2. Full MILP
1. As much as MILP brings in uncertainties around solve times (vs simple LP), makes sense for the two-market problem at hand because the charge/discharge constraint is one that needs to be respected at all times. This is the approach I am choosing and the package will be built around that.


### C. Data Loading
Simple dataclasses to load in the Excel files, freezing the objects so that numbers don't get fudged later.
1. Pushed Claude whether upsampling the hourly data to have two half hour intervals per hour (with same price) would help the solver at all, was promptly told off and no benefit to doing it.


### D. Solver and CPU arch issues
1. PuLP + CBC was recommended by Claude, turns out CBC doesn't have a binary for ARM64. Decided to pivot and use a `highspy` solver instead, because that ships wheels cross-platform and would be easier to reproduce results with.


### E. Actual Solve
1. Two-market solve takes almost 30 mins, solving for either market by itself takes less than a minute each. Started moving in the direction of having `make` targets that produce results for the single-market runs.
2. There is still an option to trigger the two-market runs with a warning that it will take ~30 mins to complete for someone attempting it.


### F. Tests and regressions
1. Added a `validate-checks` Claude skill to ensure that new code additions don't result in different profit numbers for the same dataset (assuming of course that the numbers produced now are correct...)
