#2021 Feb Revisions
library(tidyverse)
#setwd('T:\\Middlebury\\OneDrive - Middlebury College\\Research\\Non-Econ')

data2020 <- read_csv('2020StateFixedAccurate.csv')
#note that the last two columns counts death and economy in all tweets, not just COVID-19 tweets.
#All other ratios are with respect to COVID-19 tweets. 

attach(data2020)

finalAnswer <- tibble(
  Response = 'Test',
  Beta_0 = 0,
  Beta_1 = 1,
  Beta_2 = 1,
  Beta_3 = 1,
  Beta_4 = 1,
  R_Squared = 0.5,
  p_party = 0.1,
  p_cases = 0.1,
  p_deaths = 0.1,
  p_tests = 0.1
)


for (name in colnames(data2020)) {
  if (str_detect(name, 'ratio')) {
    LMmodel <- lm(data2020[[name]] ~ R.D + Cases_per_100k + Death_per_100k + Test_per_population, data = data2020)
    #print(name)
    #plot(LMmodel) do this to check for Homoscedastucity
    modelInfo <- summary(LMmodel)
    finalAnswer <- finalAnswer %>% 
      add_row(Response = name, Beta_0 = modelInfo$coefficients[1], Beta_1 = modelInfo$coefficients[2], Beta_2 = modelInfo$coefficients[3],
              Beta_3 = modelInfo$coefficients[4],Beta_4 = modelInfo$coefficients[5], R_Squared = modelInfo$r.squared, p_party = modelInfo$coefficients[17],
              p_cases = modelInfo$coefficients[18], p_deaths = modelInfo$coefficients[19], p_tests = modelInfo$coefficients[20])
  }
  
}

finalAnswer <- finalAnswer %>% slice(2:10)
write_csv(finalAnswer,'Regression Info.csv')


###############Other testing stuff
oldOne <- read_csv('2020_state_fixed.csv')
multi <- lm(Vaccine_tweet_ratio ~ R.D + Cases_per_100k + Death_per_100k + Test_per_population, data = data2020)
summary(multi)
plot(multi)


summary(lm(Cases_per_100k ~ Test_per_population, data = data2020))

ggplot(data2020,aes(Tech_tweet_ratio,Death_per_100k)) + geom_text(aes(label = ABV)) + geom_smooth(method = lm)

