#!/usr/bin/env python3

import urllib.request
from html.parser import HTMLParser
from html.entities import name2codepoint
import re

url = 'http://translate.sourceforge.net/wiki/l10n/pluralforms'
html = urllib.request.urlopen(url).read().decode('utf-8')

class Parser(HTMLParser):
  def __init__(self):
    HTMLParser.__init__(self)

    self.data = ''
    self.current_node = []
    self.in_td = False
    self.below_td = 0

    self.rules = {}

  def handle_current_node(self):
    code, name, rule = self.current_node
    m = re.match(r'^ *nplurals *=*(\d+); *plural *=(.*);', rule)
    if not m:
      return

    nplurals = int(m.group(1))
    rule = m.group(2).replace(';', '').strip()

    rule = re.sub(r'^\(?n *([\<\>\!\=]{1,2}) *(\d+)\)?$', r'n\1\2 ? 1 : 0', rule)
    rule = rule.replace('and', '&&')
    rule = rule.replace('or', '||')

    if '?' not in rule and rule != '0':
      rule += ' ? 1 : 0'

    if rule in self.rules:
      self.rules[rule].append((code, name, nplurals))
    else:
      self.rules[rule] = [(code, name, nplurals)]

  def handle_starttag(self, tag, attrs):
    if self.in_td:
      self.below_td += 1
      return
    self.in_td = tag == 'td'

  def handle_endtag(self, tag):
    if self.below_td:
      self.below_td -= 1
      return
    if not self.in_td or tag != 'td':
      return

    self.in_td = False
    self.data = self.data.strip()

    field = len(self.current_node)

    if (field == 0 and re.match(r'^[a-zA-Z_]{2,5}$', self.data)) or field in [1, 2]:
      self.current_node.append(self.data)
      if field == 2:
        self.handle_current_node()
        self.current_node = []
    else:
      self.current_node = []

    self.data = ''

  def handle_data(self, data):
    if self.in_td and self.below_td == 0:
      self.data += data

  def handle_entityref(self, name):
    if self.in_td:
      self.data += chr(name2codepoint[name])

parser = Parser()
parser.feed(html)

rules = [rule for rule in parser.rules.items()]
rules.sort(key = lambda rule: (str(rule[1][0][2]) + rule[0]))

print('switch (isoLanguageCode) {')
for rule, langs in rules:
  last_forms = 0
  langs.sort(key = lambda lang: lang[0])
  for code, name, forms in langs:
    last_forms = forms
    space = '  '
    if len(code) == 3:
      space = ' '
    print('    case "%s":%s// %s' % (code, space, name))
  if last_forms == 1:
    print('        // %d form' % last_forms)
  else:
    print('        // %d forms' % last_forms)
  print('        return %s;' % rule)
print('    default:')
print('        return n != 1 ? 1 : 0;')
print('}')
