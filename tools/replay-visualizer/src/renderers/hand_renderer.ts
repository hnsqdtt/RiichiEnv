import { TileRenderer } from './tile_renderer';

export class HandRenderer {
    static renderHand(hand: string[], melds: any[], playerIndex: number): HTMLElement {
        // Hand & Melds Area
        const handArea = document.createElement('div');
        Object.assign(handArea.style, {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            width: '580px',
            height: '56px',
            position: 'absolute',
            bottom: '0px',
            left: '50%',
            transform: 'translateX(-50%)'
        });

        // Closed Hand - Anchor Left
        const tilesDiv = document.createElement('div');
        Object.assign(tilesDiv.style, {
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'flex-start',
            flexGrow: 1 // Let it take available space but align start
        });

        const totalTiles = hand.length + melds.length * 3;
        const hasTsumo = (totalTiles % 3 === 2);

        hand.forEach((t, idx) => {
            const tDiv = document.createElement('div');
            tDiv.style.width = '40px'; tDiv.style.height = '56px';
            tDiv.innerHTML = TileRenderer.getTileHtml(t);
            if (hasTsumo && idx === hand.length - 1) tDiv.style.marginLeft = '12px';
            tilesDiv.appendChild(tDiv);
        });
        handArea.appendChild(tilesDiv);

        // Melds (Furo)
        const meldsDiv = document.createElement('div');
        Object.assign(meldsDiv.style, {
            display: 'flex',
            flexDirection: 'row-reverse',
            gap: '2px',
            alignItems: 'flex-end'
        });

        if (melds.length > 0) {
            melds.forEach(m => {
                this.renderMeld(meldsDiv, m, playerIndex);
            });
        }
        handArea.appendChild(meldsDiv);
        return handArea;
    }

    private static renderMeld(container: HTMLElement, m: { type: string, tiles: string[], from: number }, actor: number) {
        const mGroup = document.createElement('div');
        Object.assign(mGroup.style, {
            display: 'flex',
            alignItems: 'flex-end',
            marginLeft: '5px'
        });

        // Determine relative position of target: (target - actor + 4) % 4
        // 1: Right, 2: Front, 3: Left
        const rel = (m.from - actor + 4) % 4;

        const tiles = [...m.tiles]; // 3 for Pon/Chi, 4 for Kan

        // Define Column Structure
        interface MeldColumn {
            tiles: string[];
            rotate: boolean;
        }
        let columns: MeldColumn[] = [];

        if (m.type === 'ankan') {
            // Ankan: [Back, Tile, Tile, Back]
            tiles.forEach((t, i) => {
                const tileId = (i === 0 || i === 3) ? 'back' : t;
                columns.push({ tiles: [tileId], rotate: false });
            });
        } else if (m.type === 'kakan') {
            const added = tiles.pop()!;
            const ponTiles = tiles; // 3 remaining

            // Pon Logic
            const stolen = ponTiles.pop()!;
            const consumed = ponTiles; // 2 remaining

            // Reconstruct Pon cols
            if (rel === 1) { // Right
                // [c1, c2, stolen(Rot)]
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
                columns.push({ tiles: [stolen, added], rotate: true });
            } else if (rel === 2) { // Front
                // [c1, stolen(Rot), c2]
                if (consumed.length >= 2) {
                    columns.push({ tiles: [consumed[0]], rotate: false });
                    columns.push({ tiles: [stolen, added], rotate: true });
                    columns.push({ tiles: [consumed[1]], rotate: false });
                } else {
                    // Fallback
                    consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
                    columns.push({ tiles: [stolen, added], rotate: true });
                }
            } else if (rel === 3) { // Left
                // [stolen(Rot), c1, c2]
                columns.push({ tiles: [stolen, added], rotate: true });
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
            } else {
                // Self (Shouldn't happen)
                [...consumed, stolen, added].forEach(t => columns.push({ tiles: [t], rotate: false }));
            }
        } else if (m.type === 'daiminkan') {
            // Open Kan
            const stolen = tiles.pop()!;
            const consumed = tiles; // 3 remaining

            if (rel === 1) { // Right
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
                columns.push({ tiles: [stolen], rotate: true });
            } else if (rel === 2) { // Front
                if (consumed.length >= 3) {
                    columns.push({ tiles: [consumed[0]], rotate: false });
                    columns.push({ tiles: [consumed[1]], rotate: false });
                    columns.push({ tiles: [stolen], rotate: true });
                    columns.push({ tiles: [consumed[2]], rotate: false });
                } else {
                    columns.push({ tiles: [consumed[0]], rotate: false });
                    columns.push({ tiles: [consumed[1]], rotate: false });
                    columns.push({ tiles: [stolen], rotate: true }); // Fallback
                }
            } else if (rel === 3) { // Left
                columns.push({ tiles: [stolen], rotate: true });
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
            } else {
                [...consumed, stolen].forEach(t => columns.push({ tiles: [t], rotate: false }));
            }
        } else {
            // Pon / Chi
            const stolen = tiles.pop()!;
            const consumed = tiles; // 2 remaining

            if (rel === 1) { // Right
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
                columns.push({ tiles: [stolen], rotate: true });
            } else if (rel === 2) { // Front
                if (consumed.length >= 2) {
                    columns.push({ tiles: [consumed[0]], rotate: false });
                    columns.push({ tiles: [stolen], rotate: true });
                    columns.push({ tiles: [consumed[1]], rotate: false });
                } else {
                    consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
                    columns.push({ tiles: [stolen], rotate: true });
                }
            } else if (rel === 3) { // Left
                columns.push({ tiles: [stolen], rotate: true });
                consumed.forEach(t => columns.push({ tiles: [t], rotate: false }));
            } else {
                [...consumed, stolen].forEach(t => columns.push({ tiles: [t], rotate: false }));
            }
        }

        // Render Columns
        columns.forEach(col => {
            const div = document.createElement('div');
            if (col.rotate) {
                // Rotated Column
                Object.assign(div.style, {
                    display: 'flex',
                    flexDirection: 'row', // Stack horizontally since it's rotated? No, if we want to mimic stacking vertically in rotated space...
                    // Wait, implementation in renderer.ts was:
                    // transform: rotate(90deg)
                    // and inside elements are stacked?
                    // Actually, let's look at renderer.ts implementation details we're replacing.
                    // It was constructing `inner` div.
                    // But for Kakan (stacked), we need to see how it was done.

                    // Actually, renderer.ts logic for kakan:
                    // columns.push({ tiles: [stolen, added], rotate: true });
                    // And then:
                    // if (col.rotate) { ... transform: 'rotate(90deg)' ... }
                    // col.tiles.forEach(...) -> appended to div.
                    // So they are stacked inside the rotated div.
                    // If flex-direction is row (default), they stack horizontally.
                    // But if rotated 90deg, horizontal becomes vertical visually?
                    // Let's check renderer.ts... it didn't specify flex-direction for the rotated container.
                    // It just appended children. Divs block-stack by default.
                    // So they stack vertically in unrotated space.
                    // When rotated 90deg, vertical stack becomes horizontal stack?
                    // Wait, `transform: rotate(90deg)` rotates the whole container.
                    // Let's copy the logic exactly.
                });

                Object.assign(div.style, {
                    width: '42px', // Rotated height becomes width (42px)
                    height: '42px', // Match upright height
                    position: 'relative',
                    marginLeft: '4px',
                    marginRight: '4px'
                });

                // Wrapper to rotate
                const rotator = document.createElement('div');
                Object.assign(rotator.style, {
                    transform: 'rotate(90deg)',
                    transformOrigin: 'center center',
                    width: '100%',
                    height: '100%',
                    display: 'flex', // Use flex to stack
                    gap: '0px',
                    justifyContent: 'center',
                    alignItems: 'center'
                });

                // ... (Kakan logic comments)

                col.tiles.forEach((t, idx) => {
                    const inner = document.createElement('div');
                    inner.innerHTML = TileRenderer.getTileHtml(t);
                    Object.assign(inner.style, {
                        width: '30px',
                        height: '42px',
                        display: 'block' // Ensure block
                    });

                    // Kakan stacking logic:
                    // If multiple tiles (Kakan), we stack them.
                    // Since we are in a flex center/center rotated div, they will stack horizontally (visually vertical).
                    // We might need negative margins to overlap if desired, but default stacking is fine for 2D.
                    // Actually, for Kakan, we want the second tile to be "above" (visually top).
                    // In a row-reverse or just normal row?
                    // Let's standard append.

                    rotator.appendChild(inner);
                });
                div.appendChild(rotator);
            } else {
                // Upright
                Object.assign(div.style, {
                    width: '30px',  // Reduced from 40px to match meld scale
                    height: '42px', // Reduced from 56px to match meld scale
                    display: 'flex',
                    alignItems: 'flex-end',
                    justifyContent: 'center'
                });
                if (col.tiles.length > 0) {
                    div.innerHTML = TileRenderer.getTileHtml(col.tiles[0]);
                }
            }
            mGroup.appendChild(div);
        });

        container.appendChild(mGroup);
    }
}
