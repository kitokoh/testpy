specification tech et notes.
voila ce que je viens direr un produit a des dimention et son poid nest ce pas le poit cest simple ca peut etre un champs que tu porra ajouter pour les dimention un produit donnee ppeut avoirdes dimentions les dismentions ca eut etre les valeur pour les infos suivant ABCDEFGHIJtous ne sont pas obligatoire dans le table dimention faut aussi stocker l image technique dans la meme table doc en gros une dimentions cest uneimage technniqe avec les dimention qui sont de A a J et tu ajouter un nouveau tab nomee dimentions dans le quel je pourrais gerer les dimetionnions  tuyu me prepare les dialog necessaire pour gerer ca et ajouter les dimention a un produit donnit donne ajouter a un client donnee aussi ajoute moi un autre tab ou je pourrait inserer les regles ou notes  ppour les document dans cette tap on porra jouter les notes de proforma  de packintlist ou dun autre qui doit se trouver au bas de page pour un client donnee en la liste faut filtrrer par langue et le note peut avoir pluieur ligne dinsturction jedoit dans cette espace pouvoir lesmmanupuler directement dans le dtableau dedier a cela  genre ce que je supprime dans le tableau ou que la ligne que je saisi dans le tablau soit automatiqument enregistrer 

premiere connexion voila ce quil nous faut actuelemnt fait de sorte que lors que lon demarre cette applicaiton pour la priere fois alors de modal qui demande a ajouter un nouveau client la saffiche dune maniere sypatique et demande a lutilisateur dinser les info concernant son entreprise  puis luis demande  ajouter les vendeur sache que les vendeur eu ill nont pas que des nom il on aussi des numeros detelephone et mail aussi   puis le programme de mande d jouter un techniciens puis invite d ajouter un nouveau client pour commencer  une fois que le gars ajoute les infos de son enresprise un mesage sypatique lui sera affichee si possiblee meme leffet stylistique de feu dartifice puis  le progrmme va lui demande dajouter un premier clent pour demarrer aussi en haut a caute des quatre element de statistique la ajoute un autre pour dire my score que je te laisse la deffinition et limplemetaiton si tu as compris ce que je vien de dire 

preparer les document 
des beau documents
envoyer par mail 
envoyer par whatssap

les documents lessepts
deja je dois te faire remarqueer ue lors du premier demarrage de notre applictionil ya des doument par defaut qui s ajoute comme templates les document quinou interresse ici sont les document du types html ces document doivnet etre capable de recuperer  les infos nessaire dynamiquement lors que je clique sur le butons pdf present dans le tab document mais malheureusemnt pour le moment cest seul la coverpage qui reuissia recuperer ses info et generer un truc plus ou moins acceptable ce que jedois te dier cest  de faire desorte quechacun de nos 7 models html soit cpapalbe non seulement de recuperer toutes les infos qui lui son necessairer dynamiquement pour generr un pdf util mais il doivent aussi etre en terme de disign style termes utiliser et autre structure au top de top si jutlise un model par exemple de proforma en arable alors il recumerer directement les produiten arabe ajouter a  lespace de ce client il recuperer les info du client comme le nom de son entreprise ou autre comme les info de  son contact principal et autre les prix et la somme et genrer le df directement utlisable en y ajouter les remarques et notes du proforma meme chose si on veut plutot generer le pakking list  ou autre documement j ai les meme exigigence pour gerer tout les sept documement et si tu as besoin dune info pour un document donnee qui manque dans ma sturcture de base de donnee actuelle n hesite surtout pas a ajouter 

en un oui je parle bien de ces sept document en html du model template pour le disign et style de ces document je prefer te laisser exprimer ton genie normalement lors de l ajout dun produit on selectione une langue donc si on a ajouter par exemple un model de proforma ou de paking list en anglais alors en cliquant sur pdf il va chercher les produit ajouter a ce client sous la bannere en si riens nesajouter il ne generer pas le pdf mais en lieu et place un message sympatique nousinvitant a ajouter les produit en aglaisaussi tu peux faire de sorte que lors que un produit est ajouter dans une langue x on peux ajouter son equivalenet dans une langue y sans y etre systematiquement obliger biensur dans ce cas en ajoutant un produit a un client donne dans la langue x alors automatiquement si le model necessite le produit en langue y et que ceci existait deja le programme lajoute automatiquement a ce client et au document tu pourra aussi nous donnee la possibilite de filtrer les produit selon leurs langue dans la liste des produits present dans notre tabs dedier aux produit . yes you cans propose shema changes if needeed no any problem. yes enterme de prioriter on a d abord le proforma puis le specification technique puis tu peux toi meme me classifier les autres comme tu voudra ce que je veux cest une solutions robuste et utiles




regarde ce que il me faut actuelement cest de faire de sorte que en terme de disign tout les modal present dans main.py soit au top de top 
apporte tout amelioration stylistique et de disigne  pour ce file main.py 

style globale 
regarde depose le buton cree document a la place du button nomer supprime present a cote du buton ouvir dans le tab nomee  document  et tu le renome ajouter doccument je pense meme en eterme dordre il doit venir avant le butons actualisaer car  il est le plus solliciter dans ccette tabe. et la place ocupper actuelement par le button nomee cree document doit avoir un autre buton nomee envoyer mail qui ouvre un modal qui permet denvoyer lemail ce derneier nodal nouspermet notament de selectionner un model de mail et de lenvoyer .  et aussila partie dediee aux note prend beaucoup despace si tu peut faire de sorte qui disparaisse par defaut et n apparraisse qque sis soliciter caserrais mieu trouve un moyer mais lespace  quil aucupe doit d abord appartenir a  la sections des liste et en y cliquant dessus alors il apparait . aussi enterme des style et disisg globoal fait de sorte que lexperience ulilisateur soit le plus unique et le plus sympatiquie possible 

doc par defaut
maintenant en ce qui concerne les document deja arrange les document html qui s ajoute  comme template par defaut dans l applicatyion  ces document doivent etrer un proforma moderne et complet  en deux page car la deuxieme doit avoir les conditions et les notes une document our les specificationtechnique qui peu avoir jus qua trois pages  la premiere pagededier  a limage  technique plus les dimentions et les deux autre doivent avoir les ccontditions sur les materieaux et autres  un document pour le paking liste qqui doit aussi etre le plus moderne et complet possible puis unne page de garde avec bordure de page et tout les disigns moderne possible  un contrats de vente  avec les max des condition possible en deux page max et toujours le plus pro et le plus stylee possible  un certificati de garrantie  en une page le plus complet possible egalment et  aussi tu me cree une page de contact dans cette page nous pourrons tout simplement avoir les contat intervenant dans le projet genre le vendeur le technicient et le  ou les contacts client  optes pour un format  en tableau fait de sorte que tout ces document puiisse avoir en haut de page le logo de lentreprise avec  le titre du document au minimum . tu vas en parcourant mon main.py te rendre compte que certain de ces document existe deja et sont generer lors du premier demarrage de l application mais arrage les tous et ajoute aussi mes nouvelle exigence et enfin fait que ca soit vriment fonctionnelle genre en ajoutant un nouvau document a un client donner alors le template que tu me propose doit etre capable de recuperer et remplir automatiquement tout les infos dynamique quil pourra recuperer aussi comme tu va le remarquer normalment je veux ces document dans les different langue de mon applicaiton mais peut etre commencaon daord avec le francais si tout est bon on va plutard les traduires 

le mail et son envoie 
maintenant l envoie des  document par mail doit respectier un principe  de globalisateion lorsquon cherche denvoyer un mail a un utlisateur donnee deja le progrme doit etre cpable de recuperer les info du client  en question sil a un ou plusier contact le programme doit aller recupere les adresse mail directement des contact du client en question pour les pieces join tu me liste les document pdfs prioritairement  en nous donnant la possibilter de chocher pour choisir ceux quon veuxenvoyer a lutilsteur en pj mais aussi la possibilte de pouvoir selection des document d autre extention et ceci grace a un filtre qui comme je dit  filtrer les document  en pdf dabord  aussi le programme selon la langue de lutilsateur me permet de selectionner un model cd corp de mail prealablement  ajouter ces modeles poeuvent etre  du txtt de word  ou  du html  oon peux bien evidement pouvoir aussi ajouter facilement un nouveaux  model les modle slon filtrer selon la langue par defaut de lutilisateur bien que lon peut modfier  pour lui envoyer un mail dans une langue de notre choix  aussi les document auquel tu me donnera la pssiblie de chosir ne sera pas sela de la liste des document affecter a ce client mais aussi je dois pouvoir selectionner parmi les documents present dans le dossier document utilitaire ces document peuvent etrer un catalogue une liste de prix ou autre document  liee a notre entreprise  donc  voici lidee je te laisse le developpe a toi de proposer les models de texts egalement  tout doit etre pro max plus





regarde dans ma gestion des contacts je vais te demander d ameliorer certains truc normalement doit avoir beaucop plus de champs meme si les champs que jes actuelement  suffisent largement met les autre chmps colpasble lors de l jout dun nouveua ccontact ou meme lors de sa modifcation pour le visuelle tu laisee le tableua tle quil est actulement mais la base de donne doit etre pretes cest de ca d il s agit donc pour ta gouverne je te montre un peu ce quil peu y a voir dans la table prend les nom de terme tout simplement ajoute les a la table sans les rend re obligatoire et mieux cahe les avec une case a coche qui par defut n est pas activee mais si activrer alors le modal s agrandit et donne la pooibilite d inserer tout les champs {
  "names": [{
    "givenName": "John",
    "familyName": "Doe",
    "displayName": "John Doe"
  }],
  "phoneNumbers": [{
    "value": "+33612345678",
    "type": "mobile"
  }],
  "emailAddresses": [{
    "value": "john.doe@example.com",
    "type": "home"
  }],
  "addresses": [{
    "formattedValue": "123 Rue Exemple, Paris, France",
    "streetAddress": "123 Rue Exemple",
    "city": "Paris",
    "region": "Île-de-France",
    "postalCode": "75000",
    "country": "France"
  }],
  "organizations": [{
    "name": "Doorika",
    "title": "Responsable Commercial"
  }],
  "birthdays": [{
    "date": {
      "year": 1990,
      "month": 6,
      "day": 15
    }
  }],
  "notes": ["Client fidèle depuis 2018"]
}



