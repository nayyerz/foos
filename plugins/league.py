#!/usr/bin/python3

import time
import logging
import json

from foos.bus import Bus, Event
from foos.ui.ui import registerMenu
import config
import random
logger = logging.getLogger(__name__)


class Plugin:
    def __init__(self, bus):
        self.bus = bus
        self.bus.subscribe(self.process_event, thread=True)
        self.games = []
        self.current_game = 0
        self.enabled = False
        self.points = {}
        self.teams = {}
        registerMenu(self.getMenuEntries)

    def setPlayers(self):
        g = self.games[self.current_game]
        self.teams = {"yellow": [g[0], g[1]],
                      "black": [g[2], g[3]]}
        self.bus.notify(Event("set_players", self.teams))

    def clearPlayers(self):
        self.teams = {"yellow": [], "black": []}
        self.bus.notify(Event("set_players", self.teams))

    def process_event(self, ev):
        now = time.time()
        if ev.name == "start_competition":
            p = ev.data['players']
            self.points = dict([(e, 0) for e in p])
            # shuffle players
            random.shuffle(p)
            # games is the full combination of players
            self.games = [p, [p[0], p[2], p[1], p[3]], [p[0], p[3], p[1], p[2]]]
            self.current_game = 0
            self.enabled = True
            self.bus.notify(Event("reset_score"))
            self.bus.notify(Event("set_game_mode", {"mode": 5}))
            self.setPlayers()

        if ev.name == "win_game" and self.enabled:
            self.calcPoints(ev.data['team'])
            self.current_game += 1
            if self.current_game < len(self.games):
                self.setPlayers()
            else:
                self.bus.notify(Event("end_competition", {'points': self.points}))
                self.enabled = False
                self.clearPlayers()

    def calcPoints(self, team):
        for p in self.teams.get(team, []):
            self.points[p] = self.points[p] + 1

    def getMenuEntries(self):
        def q(ev):
            def f():
                self.bus.notify(ev)
                self.bus.notify(Event("menu_hide"))
            return f

        try:
            with open(config.league_file) as f:
                comp = json.load(f)
                menu = []
                for div in comp:
                    name, games = div[0], div[1]
                    mgames = []
                    for g in games:
                        ev = Event('start_competition', {"players": g, "division": name})
                        mgames.append((", ".join(g), q(ev)))

                    mgames.append(("", None))
                    mgames.append(("« Back", None))

                    menu.append((name, mgames))

                menu.append(("", None))
                menu.append(("« Back", None))

                return [("League", menu)]
        except Exception as e:
            logger.error(e)
            return []