#! /usr/bin/python3
import requests
import re
import cv2
import pytesseract
import sys

# Showdown replay regexes
damage_pattern = r'^\|move\|.+?: (.+?)\|(.+?)\|'
death_pattern = r': (.+?)\|0 fnt'
switch_pattern = r'^\|(?:switch|replace)\|.+?: (.+?)\|(.+?), L50'

# Video regexes
used_pattern = r'(?:The opposing |^ *)(.+?) used (.+?)!'
fainted_pattern = r'(?:The opposing |^ *)(.+?) fainted!'

def trace(line):
  trc_file = "trace.txt"
  with open(trc_file, "a") as f:
    f.write(line + "\n")

def analyze_replay(lines):
  trace("analysis")

  results = {}
  for line in lines:
    match = re.search(damage_pattern, line)
    if match:
      last_attacker = match.group(1)

    match = re.search(death_pattern, line)
    if match:
      last_death = match.group(1)
      if last_attacker == last_death:
        continue

      prev_kills, prev_deaths = \
        results.get(last_attacker, (0, 0))
      results[last_attacker] = (prev_kills + 1, prev_deaths)
      
      prev_kills, prev_deaths = \
        results.get(last_death, (0, 0))
      results[last_death] = (prev_kills, prev_deaths + 1)
  return results

def clean_nicknames(results, lines):
  trace("clean nicknames")

  nick_to_species = {}
  clean_results = {}
  for line in lines:
    match = re.search(switch_pattern, line)
    if match:
      nickname = match.group(1)
      species = match.group(2)
      nick_to_species[nickname] = species
  for nickname, kd in results.items():
    species = nick_to_species[nickname]
    clean_results[species] = kd
  return clean_results 

def video_to_lines(path):
  trace("video to lines")
  trace(path)

  count = 0
  success = True
  lines = []
  processed_lines = []
  attacker = None
  killed = None
  move = None

  vidcap = cv2.VideoCapture(path)

  while success:
    success,image = vidcap.read()
    if count % 20 == 0:
      cropped = image[500:600, 200:1000]
      gray_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
      ret, thresholded_image = \
        cv2.threshold(gray_image, 200, 255, cv2.THRESH_TOZERO)
      text = pytesseract.image_to_string(thresholded_image)
      lines.append(text)
    count += 1

  for line in lines:
    match = re.search(used_pattern, line)
    if match:
      if match.group(1) != attacker:
        attacker = match.group(1)
        move = match.group(2)
        processed_lines.append(f"|move|p1a: {attacker}|{move}|")
    
    match = re.search(fainted_pattern, line)
    if match:
      attacker = None
      move = None
      if match.group(1) != killed:
        killed = match.group(1)
        processed_lines.append(f"|-damage|p1a: {killed}|0 fnt")
    
  return processed_lines

def showdown_replay_to_lines(replay_url):
  trace("replay to lines")
  trace(replay_url)

  clean_replay_url = replay_url.strip().replace("?p2", "")
  log_url = clean_replay_url + ".log"
  response = requests.get(log_url)
  replay_log = response.text
  return replay_log.split("\n")

def get_stats_replay(thing):
  trace("line in file: " + thing) 

  replay_lines = []
  if thing.startswith("http"):
    replay_lines = showdown_replay_to_lines(thing)
  else:
    replay_lines = video_to_lines(thing)
  results = analyze_replay(replay_lines)
  if thing.startswith("http"):
    results = clean_nicknames(results, replay_lines)
  return results

def main():
  input_file = 'input.txt'
  output_file = 'output.txt'

  aggregate_kills = {}

  with open(input_file, 'r') as f:
    for line in f:
      kda = get_stats_replay(line)
      trace("results")
      trace(str(kda))
      for pokemon, (kills, deaths) in kda.items():
        prev_kills, prev_deaths, prev_appearences = \
          aggregate_kills.get(pokemon, (0, 0, 0))
        aggregate_kills[pokemon] = (prev_kills + kills,
                                    prev_deaths + deaths,
                                    prev_appearences + 1)
  with open(output_file, 'w') as f:
    for pokemon, (kills, deaths, appearences) in \
      sorted(aggregate_kills.items()):
      f.write(f"{pokemon}: kills={kills}, "
              f"deaths={deaths}, appearances={appearences}\n")

if __name__ == '__main__':
  main()
