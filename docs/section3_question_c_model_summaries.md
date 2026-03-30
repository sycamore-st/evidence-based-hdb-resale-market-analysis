# Section 3 Question C Model Summaries

## Difference-in-Differences Model

Source: [S3Qc_model_did_summary.txt](/outputs/section3/results/S3Qc_model_did_summary.txt)

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              log_price   R-squared:                       0.870
Model:                            OLS   Adj. R-squared:                  0.869
Method:                 Least Squares   F-statistic:                     5838.
Date:                Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                        11:48:27   Log-Likelihood:                 13198.
No. Observations:               13713   AIC:                        -2.636e+04
Df Residuals:                   13694   BIC:                        -2.621e+04
Df Model:                          18                                         
Covariance Type:                  HC3                                         
===============================================================================================
                                  coef    std err          z      P>|z|      [0.025      0.975]
-----------------------------------------------------------------------------------------------
Intercept                      12.2796      0.025    498.803      0.000      12.231      12.328
C(flat_type)[T.3 ROOM]          0.0710      0.024      2.918      0.004       0.023       0.119
C(flat_type)[T.4 ROOM]          0.1188      0.025      4.783      0.000       0.070       0.167
C(flat_type)[T.5 ROOM]          0.1382      0.026      5.404      0.000       0.088       0.188
C(flat_type)[T.EXECUTIVE]       0.1598      0.027      5.940      0.000       0.107       0.212
C(town)[T.BUKIT PANJANG]       -0.1686      0.005    -37.463      0.000      -0.177      -0.160
C(town)[T.BUKIT TIMAH]          0.3341      0.009     38.783      0.000       0.317       0.351
C(town)[T.CHOA CHU KANG]       -0.1938      0.003    -72.239      0.000      -0.199      -0.189
C(transaction_year)[T.2013]     0.0437      0.003     16.671      0.000       0.039       0.049
C(transaction_year)[T.2014]    -0.0246      0.003     -8.577      0.000      -0.030      -0.019
C(transaction_year)[T.2015]    -0.0796      0.003    -28.385      0.000      -0.085      -0.074
C(transaction_year)[T.2016]    -0.0693      0.008     -8.794      0.000      -0.085      -0.054
C(transaction_year)[T.2017]    -0.0734      0.008     -9.254      0.000      -0.089      -0.058
C(transaction_year)[T.2018]    -0.0895      0.008    -11.267      0.000      -0.105      -0.074
treated                         0.0899      0.004     23.410      0.000       0.082       0.097
post                           -0.0257      0.007     -3.486      0.000      -0.040      -0.011
treated:post                    0.0521      0.004     12.427      0.000       0.044       0.060
flat_age                       -0.0091      0.000    -51.923      0.000      -0.009      -0.009
floor_area_sqm                  0.0083      0.000     68.433      0.000       0.008       0.009
==============================================================================
Omnibus:                      631.157   Durbin-Watson:                   1.216
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              937.871
Skew:                           0.424   Prob(JB):                    2.21e-204
Kurtosis:                       3.960   Cond. No.                     6.21e+03
==============================================================================

Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
[2] The condition number is large, 6.21e+03. This might indicate that there are
strong multicollinearity or other numerical problems.
```

## Pre-trend Model

Source: [S3Qc_model_pretrend_summary.txt](/outputs/section3/results/S3Qc_model_pretrend_summary.txt)

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              log_price   R-squared:                       0.861
Model:                            OLS   Adj. R-squared:                  0.861
Method:                 Least Squares   F-statistic:                     4244.
Date:                Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                        11:48:27   Log-Likelihood:                 7337.0
No. Observations:                7223   AIC:                        -1.465e+04
Df Residuals:                    7210   BIC:                        -1.456e+04
Df Model:                          12                                         
Covariance Type:                  HC3                                         
=============================================================================================
                                coef    std err          z      P>|z|      [0.025      0.975]
---------------------------------------------------------------------------------------------
Intercept                    12.3452     16.696      0.739      0.460     -20.378      45.068
C(flat_type)[T.3 ROOM]        0.0692     16.696      0.004      0.997     -32.654      32.792
C(flat_type)[T.4 ROOM]        0.1161     16.696      0.007      0.994     -32.607      32.839
C(flat_type)[T.5 ROOM]        0.1294     16.696      0.008      0.994     -32.593      32.852
C(flat_type)[T.EXECUTIVE]     0.1470     16.696      0.009      0.993     -32.576      32.870
C(town)[T.BUKIT PANJANG]     -0.1636      0.006    -28.113      0.000      -0.175      -0.152
C(town)[T.BUKIT TIMAH]        0.2808      0.012     22.704      0.000       0.257       0.305
C(town)[T.CHOA CHU KANG]     -0.1664      0.004    -45.724      0.000      -0.174      -0.159
treated                       0.0909      0.005     17.556      0.000       0.081       0.101
year_index                   -0.0298      0.001    -29.688      0.000      -0.032      -0.028
treated:year_index            0.0074      0.002      3.227      0.001       0.003       0.012
flat_age                     -0.0089      0.000    -33.318      0.000      -0.009      -0.008
floor_area_sqm                0.0078      0.000     46.839      0.000       0.007       0.008
==============================================================================
Omnibus:                      197.837   Durbin-Watson:                   1.063
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              260.265
Skew:                           0.322   Prob(JB):                     3.05e-57
Kurtosis:                       3.671   Cond. No.                     2.04e+04
==============================================================================

Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
[2] The condition number is large, 2.04e+04. This might indicate that there are
strong multicollinearity or other numerical problems.
```

## Event-study Model

Source: [S3Qc_model_event_study_summary.txt](/outputs/section3/results/S3Qc_model_event_study_summary.txt)

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              log_price   R-squared:                       0.867
Model:                            OLS   Adj. R-squared:                  0.867
Method:                 Least Squares   F-statistic:                     4865.
Date:                Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                        11:48:27   Log-Likelihood:                 13063.
No. Observations:               13713   AIC:                        -2.608e+04
Df Residuals:                   13691   BIC:                        -2.592e+04
Df Model:                          21                                         
Covariance Type:                  HC3                                         
===============================================================================================
                                  coef    std err          z      P>|z|      [0.025      0.975]
-----------------------------------------------------------------------------------------------
Intercept                      12.2652      0.026    467.591      0.000      12.214      12.317
C(flat_type)[T.3 ROOM]          0.0733      0.026      2.820      0.005       0.022       0.124
C(flat_type)[T.4 ROOM]          0.1218      0.026      4.597      0.000       0.070       0.174
C(flat_type)[T.5 ROOM]          0.1421      0.027      5.220      0.000       0.089       0.195
C(flat_type)[T.EXECUTIVE]       0.1647      0.029      5.773      0.000       0.109       0.221
C(town)[T.BUKIT PANJANG]       -0.1316      0.004    -31.299      0.000      -0.140      -0.123
C(town)[T.BUKIT TIMAH]          0.3657      0.008     43.439      0.000       0.349       0.382
C(town)[T.CHOA CHU KANG]       -0.1841      0.003    -68.376      0.000      -0.189      -0.179
C(transaction_year)[T.2013]     0.0451      0.003     15.849      0.000       0.039       0.051
C(transaction_year)[T.2014]    -0.0307      0.003     -9.990      0.000      -0.037      -0.025
C(transaction_year)[T.2015]    -0.0672      0.003    -22.975      0.000      -0.073      -0.061
C(transaction_year)[T.2016]    -0.0937      0.003    -32.148      0.000      -0.099      -0.088
C(transaction_year)[T.2017]    -0.1021      0.003    -33.442      0.000      -0.108      -0.096
C(transaction_year)[T.2018]    -0.1271      0.003    -41.658      0.000      -0.133      -0.121
flat_age                       -0.0085      0.000    -48.232      0.000      -0.009      -0.008
floor_area_sqm                  0.0083      0.000     66.667      0.000       0.008       0.009
treated_event_m4                0.0569      0.005     11.121      0.000       0.047       0.067
treated_event_m3                0.0514      0.006      8.802      0.000       0.040       0.063
treated_event_m2                0.0766      0.007     11.696      0.000       0.064       0.089
treated_event_p0                0.0963      0.006     16.143      0.000       0.085       0.108
treated_event_p1                0.1137      0.006     18.484      0.000       0.102       0.126
treated_event_p2                0.1438      0.006     22.999      0.000       0.132       0.156
==============================================================================
Omnibus:                      674.437   Durbin-Watson:                   1.197
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              975.031
Skew:                           0.455   Prob(JB):                    1.88e-212
Kurtosis:                       3.938   Cond. No.                     6.21e+03
==============================================================================

Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
[2] The condition number is large, 6.21e+03. This might indicate that there are
strong multicollinearity or other numerical problems.
```

## Distance-band Experiment Model

```text
                            OLS Regression Results                            
==============================================================================
Dep. Variable:              log_price   R-squared:                       0.881
Model:                            OLS   Adj. R-squared:                  0.880
Method:                 Least Squares   F-statistic:                     4670.
Date:                Sun, 29 Mar 2026   Prob (F-statistic):               0.00
Time:                        11:48:27   Log-Likelihood:                 13803.
No. Observations:               13713   AIC:                        -2.756e+04
Df Residuals:                   13688   BIC:                        -2.737e+04
Df Model:                          24                                         
Covariance Type:                  HC3                                         
============================================================================================================================================================
                                                                                               coef    std err          z      P>|z|      [0.025      0.975]
------------------------------------------------------------------------------------------------------------------------------------------------------------
Intercept                                                                                   12.2656      0.024    515.403      0.000      12.219      12.312
C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.0-250m]              0.2195      0.011     20.269      0.000       0.198       0.241
C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.250-500m]            0.1063      0.007     15.121      0.000       0.093       0.120
C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.500-750m]            0.0962      0.004     21.560      0.000       0.087       0.105
C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.750m-1.0km]          0.0550      0.005     11.596      0.000       0.046       0.064
C(flat_type)[T.3 ROOM]                                                                       0.0578      0.024      2.460      0.014       0.012       0.104
C(flat_type)[T.4 ROOM]                                                                       0.0990      0.024      4.130      0.000       0.052       0.146
C(flat_type)[T.5 ROOM]                                                                       0.1122      0.025      4.550      0.000       0.064       0.161
C(flat_type)[T.EXECUTIVE]                                                                    0.1351      0.026      5.230      0.000       0.084       0.186
C(town)[T.BUKIT PANJANG]                                                                    -0.1545      0.005    -33.171      0.000      -0.164      -0.145
C(town)[T.BUKIT TIMAH]                                                                       0.3134      0.010     29.917      0.000       0.293       0.334
C(town)[T.CHOA CHU KANG]                                                                    -0.1839      0.003    -67.665      0.000      -0.189      -0.179
C(transaction_year)[T.2013]                                                                  0.0428      0.003     16.674      0.000       0.038       0.048
C(transaction_year)[T.2014]                                                                 -0.0267      0.003     -9.581      0.000      -0.032      -0.021
C(transaction_year)[T.2015]                                                                 -0.0824      0.003    -30.281      0.000      -0.088      -0.077
C(transaction_year)[T.2016]                                                                 -0.0722      0.007     -9.926      0.000      -0.086      -0.058
C(transaction_year)[T.2017]                                                                 -0.0780      0.007    -10.658      0.000      -0.092      -0.064
C(transaction_year)[T.2018]                                                                 -0.0948      0.007    -12.938      0.000      -0.109      -0.080
post                                                                                        -0.0252      0.007     -3.722      0.000      -0.039      -0.012
post:C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.0-250m]         0.1416      0.014     10.059      0.000       0.114       0.169
post:C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.250-500m]       0.0875      0.010      8.360      0.000       0.067       0.108
post:C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.500-750m]       0.0402      0.005      7.435      0.000       0.030       0.051
post:C(distance_experiment_band, Treatment(reference='1.5-4.0km control'))[T.750m-1.0km]     0.0277      0.005      5.237      0.000       0.017       0.038
flat_age                                                                                    -0.0083      0.000    -46.791      0.000      -0.009      -0.008
floor_area_sqm                                                                               0.0085      0.000     72.820      0.000       0.008       0.009
==============================================================================
Omnibus:                      537.457   Durbin-Watson:                   1.294
Prob(Omnibus):                  0.000   Jarque-Bera (JB):              883.183
Skew:                           0.346   Prob(JB):                    1.66e-192
Kurtosis:                       4.033   Cond. No.                     6.21e+03
==============================================================================

Notes:
[1] Standard Errors are heteroscedasticity robust (HC3)
[2] The condition number is large, 6.21e+03. This might indicate that there are
strong multicollinearity or other numerical problems.
```
