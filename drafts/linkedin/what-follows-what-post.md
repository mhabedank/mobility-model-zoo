# LinkedIn: What follows what? (Field note, part 3)

Bild: drafts/linkedin/what-follows-what-linkedin.png
Bildnachweis: River lock with its gates opening and a push boat waiting (AI-generated, CC0)

## Post

Planen, Ticket kaufen, zum Gleis, warten, einsteigen, umsteigen, ankommen.

Diese Reihenfolge kann jeder aus dem Kopf aufschreiben. Genau deshalb hielt ich sie für den einfachen Teil.

Ich baue an einem Modell, das Customer Journeys aus Texten rekonstruiert: Beschwerden, Forenbeiträge, Interviews. Wer betroffen ist und wozu etwas dient, steht oft in einem einzigen Satz. Die Reihenfolge fast nie.

Der Grund ist banal. Eine Beschwerde beschreibt meist einen Moment.
„Der Automat hat meine Karte nicht genommen."
„Gleiswechsel, keine Durchsage."
Ein Schritt, ein Zitat, kein Davor und kein Danach.

Die Reihenfolge entsteht erst, wenn ich vier solcher Texte nebeneinanderlege. Und dann kommt sie nicht aus den Texten, sondern von mir. Weil ich weiß, wie eine Bahnfahrt geht.

Im Process Mining wäre das ein Event-Log ohne Case-ID: lauter Ereignisse, aber nichts sagt, welche zur selben Fahrt gehören. Heraus kommt die Reihenfolge, die man hineingesteckt hat.

Dazu kommt ein zweiter Effekt. Wer eine Abfolge erzählt, tut das meist, weil etwas schiefging. Die Übergänge mit Beleg sind die gescheiterten. Der glatte Pfad, um den jede Journey Map gebaut ist, steht kaum in den Daten.

Meine Konsequenz: Das Modell speichert eine Reihenfolge nur, wenn ein einzelner Text sie selbst erzählt, mit Zitat. Was erst über mehrere Texte entsteht, ist eine Hypothese und wird so markiert.

Offen ist für mich, wie man diese Hypothesen sauber prüft. Wer Journeys aus Interviews oder Beschwerden baut: Woher kommt bei euch die Reihenfolge, und wie trennt ihr sie von dem, was ihr vorher schon wusstet?

#CustomerJourney #ServiceDesign #ProcessMining #ÖPNV

## Erster Kommentar

Den stärksten Einwand gegen meinen eigenen Post habe ich selbst: Ein gut geführtes Interview ist keine Beschwerde. Da werden ganze Abläufe erzählt, mit Davor und Danach. Wie oft das in meinen Texten tatsächlich vorkommt, habe ich noch nicht gezählt. Das ist der nächste Schritt.

Zwei Dinge, die im Post keinen Platz hatten: Viele Übergänge sind gar kein „danach", sondern ein „während" („Ich hing die ganze Wartezeit in der Hotline-Schleife"). Und in manchen Netzen kauft man das Ticket vor dem Einsteigen, in anderen im Bus. Eine Zeile von links nach rechts bildet beides nicht ab.

Ausgeschrieben, mit Quellen (Schank & Abelson, Labov & Waletzky, Allen, van der Aalst):
https://mhabedank.github.io/mobility-model-zoo/notes/what-follows-what/
