"""
Evaluation dataset for the space-exploration FAISS index.

Each question lists the chunk IDs that contain the information needed to
answer it. A chunk is relevant if someone reading it would learn part of
the answer.


Index layout:
    chunks  0-58   History of Human Space Exploration
    chunks 59-67   NovaTech AI Product Handbook (a second document)
"""

GROUND_TRUTH = [
    # ------------------------------------------------------------------
    # single: the answer sits in one chunk
    # ------------------------------------------------------------------
    {
        "id": "q01",
        "kind": "multi_chunk",
        "question": "When did the Space Age begin and what event marked it?",
        "relevant": [0, 55],
        "reference_answer": "The Space Age began on 4 October 1957 with the Soviet launch of Sputnik 1, the first artificial satellite.",
    },
    {
        "id": "q02",
        "kind": "single",
        "question": "How long did Yuri Gagarin's orbit of the Earth take?",
        "relevant": [6],
        "reference_answer": "Vostok 1 completed a single orbit in 108 minutes.",
    },
    {
        "id": "q03",
        "kind": "single",
        "question": "At what altitude and speed does the ISS orbit?",
        "relevant": [20],
        "reference_answer": "About 400 km up, travelling at roughly 28,000 km/h, completing 15.5 orbits a day.",
    },
    {
        "id": "q04",
        "kind": "multi_chunk",
        "question": "When was the James Webb Space Telescope launched?",
        "relevant": [40, 57],
        "reference_answer": "JWST launched on 25 December 2021.",
    },
    {
        "id": "q05",
        "kind": "single",
        "question": "What is the record for the longest single spaceflight?",
        "relevant": [9],
        "reference_answer": "Valery Polyakov, 437 days and 17 hours aboard Mir in 1994-1995.",
    },
    {
        "id": "q06",
        "kind": "multi_chunk",
        "question": "Who were the first man and the first woman to fly in space?",
        "relevant": [6, 7, 55],
        "reference_answer": "Yuri Gagarin on 12 April 1961 and Valentina Tereshkova on 16 June 1963.",
    },
    {
        "id": "q07",
        "kind": "multi_chunk",
        "question": "What happened on the lunar surface during Apollo 11?",
        "relevant": [14, 15],
        "reference_answer": "Armstrong and Aldrin landed in the Sea of Tranquility on 20 July 1969 and spent about two and a half hours outside while Michael Collins orbited in the Command Module.",
    },
    {
        "id": "q08",
        "kind": "multi_chunk",
        "question": "Which theorists laid the groundwork for rocketry before Sputnik?",
        "relevant": [1, 2],
        "reference_answer": "Tsiolkovsky derived the rocket equation, Goddard flew the first liquid-fuelled rocket in 1926, and Oberth's theory influenced the V-2.",
    },
    {
        "id": "q09",
        "kind": "multi_chunk",
        "question": "What are the objectives of Artemis 1, 2 and 3?",
        "relevant": [34, 35],
        "reference_answer": "Artemis 1 was an uncrewed SLS/Orion flight around the Moon in late 2022, Artemis 2 carries a crew around the Moon, Artemis 3 lands astronauts near the south pole.",
    },
    {
        "id": "q10",
        "kind": "multi_chunk",
        "question": "How does the human body change in space and what do astronauts do about it?",
        "relevant": [43, 44],
        "reference_answer": "Cardiac deconditioning, 1-2% bone mineral loss per month and muscle atrophy, countered by two hours of daily exercise.",
    },
    {
        "id": "q11",
        "kind": "multi_chunk",
        "question": "Which Mars rovers has NASA operated and when did they land?",
        "relevant": [22, 23, 56, 57],
        "reference_answer": "Sojourner 1997, Spirit and Opportunity 2004, Curiosity 2012, Perseverance February 2021.",
    },
    {
        "id": "q12",
        "kind": "multi_chunk",
        "question": "Which missions have explored the outer solar system?",
        "relevant": [24, 25, 26],
        "reference_answer": "Voyager 1 and 2 from 1977, Cassini at Saturn 2004-2017, New Horizons past Pluto in 2015, Juno at Jupiter since 2016.",
    },
    {
        "id": "q13",
        "kind": "multi_chunk",
        "question": "How has SpaceX changed launch economics, and what vehicles does it fly?",
        "relevant": [28, 29],
        "reference_answer": "Falcon 9 was the first orbital-class rocket to land and reuse a booster, with 200+ reflights by 2024; Dragon carries cargo and crew, Starship is the reusable super-heavy system.",
    },

    # ------------------------------------------------------------------
    # paraphrase: the question wording differs from the document
    # ------------------------------------------------------------------
    {
        "id": "q14",
        "kind": "paraphrase",
        "question": "Why bother putting telescopes in orbit instead of on a mountain top?",
        "relevant": [38],
        "reference_answer": "Orbit avoids atmospheric absorption of certain wavelengths and the blurring from atmospheric turbulence.",
    },
    {
        "id": "q15",
        "kind": "paraphrase",
        "question": "Who managed to put a lander down near the Moon's southern pole?",
        "relevant": [32],
        "reference_answer": "India's ISRO with Chandrayaan-3 in August 2023, the fourth country to soft-land on the Moon.",
    },
    {
        "id": "q16",
        "kind": "paraphrase",
        "question": "Is anyone allowed to own an asteroid they mine?",
        "relevant": [54],
        "reference_answer": "The Outer Space Treaty of 1967 bars national appropriation of celestial bodies, though its application to commercial extraction is debated.",
    },

    # ------------------------------------------------------------------
    # multi_hop: facts must be combined from separate places
    # ------------------------------------------------------------------
    {
        "id": "q17",
        "kind": "multi_hop",
        "question": "How many years passed between the first and the last Apollo Moon landing?",
        "relevant": [14, 16],
        "reference_answer": "Three years, from Apollo 11 in July 1969 to Apollo 17 in December 1972.",
    },
    {
        "id": "q18",
        "kind": "multi_hop",
        "question": "Which crewed spaceflight accidents killed astronauts, and in which programmes?",
        "relevant": [8, 13, 18],
        "reference_answer": "Apollo 1's cabin fire in 1967, Challenger in 1986 and Columbia in 2003 in the Shuttle programme, and Komarov on Soyuz 1.",
    },
    {
        "id": "q19",
        "kind": "multi_hop",
        "question": "Which worlds are candidates for life, and which missions are going there?",
        "relevant": [25, 49, 50],
        "reference_answer": "Europa and Enceladus have subsurface oceans and Titan has complex organics; Europa Clipper launched in 2024.",
    },
    {
        "id": "q20",
        "kind": "other_document",
        "question": "What authentication method does LogiSense use for its API?",
        "relevant": [61],
        "reference_answer": "Bearer token authentication, with the API key in the Authorization header of every request.",
    },
]