-- Abre conversaciones individuales de iMessage con las 14 creadoras activas de SkinQueens
-- Ejecutar: osascript ~/VIRAL/tools/open-imessage-creators.applescript

set creators to {¬
  {"Amber Blasian", "moneyazmine@gmail.com"}, ¬
  {"Anna Edington", "annaelaine12@gmail.com"}, ¬
  {"Antonia", "munginantonia@gmail.com"}, ¬
  {"Brittany Rife", "brittanyrife1@gmail.com"}, ¬
  {"Bryanna", "bryanna.matthewsj@gmail.com"}, ¬
  {"Elise Klepper", "xo.eliseolivia@gmail.com"}, ¬
  {"Jadae Barnes", "janijadae@gmail.com"}, ¬
  {"Jersey Rios", "jerseycreates@gmail.com"}, ¬
  {"Jordyn Stover", "jordyncreatesugc@gmail.com"}, ¬
  {"Keri Dykes", "keri@pureheartservices.com"}, ¬
  {"Leilani Barbee", "leilanibugc@gmail.com"}, ¬
  {"Rain Storm", "rainstorm@raincreativenyc.com"}, ¬
  {"Shin Shields", "contentbyshin@gmail.com"}, ¬
  {"Victoria Bonilla", "theeverydayelevated.ugc@gmail.com"} ¬
}

tell application "Messages"
  activate
  repeat with creatorInfo in creators
    set creatorName to item 1 of creatorInfo
    set creatorEmail to item 2 of creatorInfo
    try
      set targetService to 1st service whose service type = iMessage
      set targetBuddy to buddy creatorEmail of targetService
      send "" to targetBuddy
    on error
      -- Si no tiene iMessage con ese email, abrir ventana nueva
      make new chat with properties {participants: {creatorEmail}}
    end try
    delay 0.5
  end repeat
end tell
