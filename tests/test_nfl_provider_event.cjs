const{test}=require('node:test'),a=require('node:assert/strict');require('../docs/dames-picks/feeds.js');const m=globalThis.DamesPicksModel;
const kickoff='2030-11-15T18:00:00Z',now=Date.parse('2030-11-15T17:00:00Z');
function row(){return {game_id:'g',player_id:'p',player:'Player',team:'A',opponent:'B',stat:'Receptions',target:'REC',line:'3',proj:'4',p_more:'.6',pick:'More',odds_type:'standard',captured_at:'2030-11-15T16:00:00Z',matchup_evidence:JSON.stringify({provider_game_id:'NFL_game_test',provider_team:'A',provider_start_time:kickoff})}}
const schedule={games:[{game_id:'g',kickoff_utc:kickoff},{game_id:'next',kickoff_utc:'2030-11-22T18:00:00Z'}]};
test('provider event matching exact team/kickoff passes',()=>a.equal(m.nfl([[row()]],schedule,now).length,1));
test('same offer cannot become next-week opponent forecast',()=>a.equal(m.nfl([[row(),{...row(),game_id:'next'}]],schedule,now).length,1));
test('unknown provider attribution hides all future forecast fields',()=>a.equal(m.nfl([[{...row(),matchup_evidence:''}]],schedule,now).length,0));
test('wrong team/time fail closed',()=>{for(const x of [{provider_team:'WRONG'},{provider_start_time:'2030-11-15T19:00:00Z'}]){const p=row();p.matchup_evidence=JSON.stringify({...JSON.parse(p.matchup_evidence),...x});a.equal(m.nfl([[p]],schedule,now).length,0)}});
test('tonight pre-rollout immutable rows retained without retrocertification',()=>a.equal(m.nfl([[{...row(),captured_at:'2026-11-13T00:00:00Z',matchup_evidence:''}]],{games:[{game_id:'g',kickoff_utc:'2026-11-13T01:15:00Z'}]},now).length,1));
test('ambiguous future row never resurfaces after its game starts',()=>a.equal(m.nfl([[{...row(),matchup_evidence:''}]],schedule,Date.parse(kickoff)+1).length,0));
