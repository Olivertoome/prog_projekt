poed = {
    "Rimi": "rimi.txt",
    "Selver": "selver.txt",
    #"Coop": "coop.txt",
    #"Prisma": "prisma.txt",
    #"Maxima": "maxima.txt",
}

def lugemine(file):
    hinnad = {}

    with open(file, "r", encoding="utf-8") as f:
        for rida in f:
            rida = rida.strip()
            osad = rida.split(",")
            toode, hind = osad
            toode = toode.strip().lower()
            hind = float(hind.strip())

            hinnad[toode] = hind

    return hinnad


def arvutamine(pood, hinnad, ostukorv):
    summa = 0.0
    #puuduvad = []

    for toode, kogus in ostukorv.items():
        if toode in hinnad:
            summa += hinnad[toode] * kogus
            #leitud_tooted.add(toode)
        #else:
            #puuduvad.append(toode)

    return summa#, puuduvad


def main():
    ostukorv = {}
    print("Sisesta tooted ostukorvi (tühja rea sisestamine lõpetab):")

    while True:
        toode = input("Toode: ").strip().lower()
        if toode == "":
            break
        
        kogus_str = input("Kogus: ").strip()
        try:
            kogus = int(kogus_str.replace(",", "."))
        except ValueError:
            print("Kogus peab olema number.")
            continue

        ostukorv[toode] = ostukorv.get(toode, 0) + kogus
    
    poodide_sum = {}
    for pood, fail in poed.items():
        hinnad = lugemine(fail)
        summa = arvutamine(pood, hinnad, ostukorv)
        poodide_sum[pood] = summa
        
    print("\nOstukorvi maksumus poodides:")
    for pood, summa in poodide_sum.items():
        print(f" - {pood}: {summa:.2f} €")
        
    odavaim_pood = min(poodide_sum, key=poodide_sum.get)
    odavaim_summa = poodide_sum[odavaim_pood]
    print(f"\nKõige soodsam pood on: {odavaim_pood} ({odavaim_summa:.2f} €)")
    
if __name__ == "__main__":
    main()    
