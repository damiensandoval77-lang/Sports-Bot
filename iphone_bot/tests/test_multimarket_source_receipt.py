"""A model run retains the provider snapshot it actually consumed."""
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import numpy as np
from iphone_bot import live_multimarket_matchup as model

class Predictor:
    def predict(self, values):
        return [10.0]

class SourceReceiptTests(unittest.TestCase):
    def test_provider_time_is_not_replaced_with_model_execution_time(self):
        now=datetime(2026,11,12,23,tzinfo=timezone.utc)
        feed={'status':'FRESH_AUTHENTIC_PRIZEPICKS_LINES','is_live':True,
              'source':'AUTHENTIC_PRIZEPICKS_PICKEM_NO_ODDS',
              'source_generated_at':'2026-11-12T22:45:00Z',
              'updated_at':'2026-11-12T22:59:00Z','picks':[]}
        item={'player':'Fixture','game':'Boston Celtics @ New York Knicks',
              'stat':'Points','line':12.5,'start':'2026-11-13T00:00:00Z',
              'market_updated':'2026-11-12T22:45:00Z'}
        records=[{'id':'123','player':'Fixture','team':'BOS','date':'2026-11-11'}]
        pack={'research_only':True,'calibrated':False,'training_seasons':model.TRAIN,
              'feature_columns':model.FEATURES,
              'validation_residual_triplets':np.zeros((1000,3)),
              'models':{s:Predictor() for s in ('PTS','REB','AST')}}
        vector={k:1.0 for k in set(model.FEATURES)|set(model.COLS)}
        with patch.object(model,'select_standard',return_value=([item],{})), \
             patch.object(model,'build_team_games',return_value={}), \
             patch.object(model,'feature_vector',return_value=(vector,None)), \
             patch.object(model,'injury_adjustment',return_value={'status':'NO_REPORTED_OUT','factor':1.0,'affected':[]}), \
             patch.object(model,'simulate',return_value={'modeled_direction':'Less','method':model.METHOD,'projection':10.0,'component_projections':{'PTS':10.0,'REB':10.0,'AST':10.0}}):
            result=model.forecasts(records,feed,pack,now=now)
        self.assertEqual(result['source_provider_generated_at'],feed['source_generated_at'])
        self.assertEqual(result['source_model_input_generated_at'],feed['updated_at'])
        self.assertNotEqual(result['source_provider_generated_at'],result['generated_at'])

if __name__=='__main__':unittest.main()
