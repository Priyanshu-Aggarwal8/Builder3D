from app.services.architect_engine import generate_architectural_layout

prompt = "A 12-story building, each floor having 2 houses, one is 2bhk, second is 3bhk house."
elements = generate_architectural_layout(prompt, 1)

print(f"TOTAL ELEMENTS GENERATED: {len(elements)}")
levels = set()
units = set()
pool_elements = []

for el in elements:
    name = el.get("name", "")
    if "pool" in name.lower():
        pool_elements.append(name)
    if "Level" in name:
        lvl = name.split("Level")[1].split()[0]
        levels.add(lvl)
    if "Unit 1" in name or "2BHK" in name:
        units.add("2BHK Unit 1")
    if "Unit 2" in name or "3BHK" in name:
        units.add("3BHK Unit 2")

print(f"STOREY LEVELS DETECTED: {len(levels)} levels -> {sorted(list(levels), key=lambda x: int(x) if x.isdigit() else 99)}")
print(f"UNITS PER FLOOR DETECTED: {units}")
print(f"POOL ELEMENTS (Should be 0): {len(pool_elements)} -> {pool_elements}")
print("\nSAMPLE LEVEL 1 & LEVEL 12 ELEMENTS:")
for el in elements[:6] + elements[-6:]:
    print(f" - [{el.get('type')}] {el.get('name')} @ Y={el.get('position')[1]:.1f}m")
