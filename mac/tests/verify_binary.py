"""Verify the exact input build and native dylib without executing either."""
import hashlib
import struct
import sys
from pathlib import Path

EXPECTED = '8ab9adf4a5900a18532f3403bd07f9515fb59f4afbc5e8ebdb795aeeaf698d57'
UUID = '34f71c89236638e192a29c400e28045a'
SYMBOLS = {
    '__ZN15PlayerCharacter11canDoActionEv': 0x1000282e0,
    '__ZN12ClientObject8doActionEP6Action': 0x10002e850,
    '__ZN3Gun5doUseEj': 0x10003f620,
    '__ZN3Gun5shootEi': 0x10003f680,
    '__ZN3Gun6updateEib': 0x100040080,
    '__ZN15PlayerCharacter8moveItemEii': 0x1000266b0,
    '__ZN15PlayerCharacter8dropItemEi': 0x100026a50,
    '__ZTV16InventoryOverlay': 0x1001eca90,
    '__ZN15PlayerCharacter7getItemEi': 0x100026d90,
    '__ZN15PlayerCharacter7addItemERK14ItemProperties': 0x100026400,
    '__ZN15PlayerCharacter9equipItemERK14ItemProperties': 0x1000262a0,
    '__ZN15PlayerCharacter6tryAddERK14ItemPropertiesPK15ItemDescription4Slot': 0x100026510,
    '__ZN4Item10createItemEP15PlayerCharacterRK14ItemProperties': 0x100044b30,
    '__ZN11ItemLibrary3getEv': 0x100045ac0,
    '__ZNK11ItemLibrary6lookupEj': 0x100045ff0,
    '__ZN4Loot5onUseEb': 0x10004cbd0,
    '__ZN9StatBoostC1Ev': 0x1001624a0,
    '__ZN9StatBoostD1Ev': 0x100162af0,
    '__ZN15PlayerCharacter9getNumPosE4Slot': 0x100026ca0,
    '__ZN11ClientWorld12addModifyInvERK9ModifyInv': 0x100015f70,
    '__ZN16InventoryOverlay7doInputEjb': 0x1000bd090,
    '__ZN15InventoryWindow11updateSlotsEv': 0x1000be040,
    '__ZN11ClientWorld9createObjEP12ClientObjecti': 0x100015910,
    '__ZN11WorldClient15handleModifyInvERK9ModifyInv': 0x1000f56c0,
    '__ZN9ModifyInvC1Ev': 0x10014d6e0,
    '__ZN16ServerConnection15startConnectionEv': 0x100086cb0,
    '__ZN16ServerConnection9connectToEPKctii': 0x100085ba0,
    '__ZN16ServerConnection11sendMessageE11MessageType': 0x100085d10,
    '__ZN16ServerConnection11sendMessageE11MessageTypeRKN6google8protobuf11MessageLiteE': 0x100085db0,
    '__ZN11PlayerInputC1Ev': 0x10014d6b0,
    '__ZN11PlayerInputD1Ev': 0x100159ad0,
    '__ZN11ClientWorld8serverDTEv': 0x1000156b0,
    '__ZN11WorldClient12doTimePassesEv': 0x1000f53f0,
    '__ZN11ClientWorld17doThrottledUpdateEP15ForeignSubWorldi': 0x100016e50,
    '__ZN8TimeUtil5NowMSEv': 0x10000d880,
    '__ZN16ServerConnection4doIOEv': 0x100086240,
    '_LZ4_decompress_safe': 0x1001874a0,
    '__ZN5World8addDeltaERK5Delta': 0x10006a740,
    '__ZN11ClientWorld17handleWorldUpdateERK11WorldUpdate': 0x1000163c0,
    '__ZN12compressUtil10decompressEPKciPNSt3__112basic_stringIcNS2_11char_traitsIcEENS2_9allocatorIcEEEE': 0x100006da0,
    '__ZN11WorldClient17handleServerDeltaE11MessageTypePKci': 0x1000f4aa0,
    '__ZN9deltaUtil6decodeE11MessageTypePKciP5Delta': 0x100003e70,
    '__ZN9deltaUtil15decompressDeltaEPKciP5Delta': 0x100003940,
    '__ZN5Stage19handleKeyboardEventEii': 0x100076060,
    '__ZTV8Controls': 0x1001eba80,
    '__ZTV12KeyRemapPage': 0x1001ec290,
    '__ZTV14ClickableLabel': 0x1001e9a60,
    '__ZN8Controls18handleAddedToStageEv': 0x1000addd0,
    '__ZN8Controls19handleKeyboardEventEii': 0x1000adeb0,
    '__ZN8Controls21handleResetToDefaultsEv': 0x1000adf80,
    '__ZN12KeyRemapPageC2EPK11ClientInput': 0x1000b38d0,
    '__ZN14ClickableLabelC2EPKcS1_ijj': 0x10006dd40,
    '__ZN5LabelC2EPKcS1_ijiji': 0x1000726b0,
    '__ZN5Label7setTextEPKc': 0x100072a70,
    '__ZN5Label8setColorEj': 0x1000729b0,
    '__ZN18UIElementContainer8addChildEP9UIElement': 0x100077e60,
    '__ZN9UIElement8fillRectEiiiij': 0x100077bb0,
    '__ZN4Tabs9handleTabEi': 0x1000b60c0,
    '__ZN16HitNumberGraphicC2EP9WorldViewsP11WorldObjectibbjiii': 0x1000da9c0,
    '__ZN16HitNumberGraphic4drawEii': 0x1000dacf0,
    '__ZN16HitNumberGraphic6isDoneEi': 0x1000dacd0,
    '__ZTV16HitNumberGraphic': 0x1001ee2f0,
    '__ZN13NumberTextureC2EPKcijiji': 0x10008dee0,

    '__ZN8MainMenuC2Eii': 0x1000bfaf0,
    '__ZN10GameClient14updateIdleKickEi': 0x10007ac80,
    '__ZN5Chest9throwLootEv': 0x10002e140,
    '__ZTV5Chest': 0x1001e5370,
    '__ZTV4Loot': 0x1001e83d0,
    '__ZNK4Loot17interactItemPropsEv': 0x10004cef0,
    '__ZN9WorldView17handleScreenShakeEii': 0x1000e0c90,
    '__ZN9WorldView11screenFlashEiiij': 0x1000e0cb0,
    '__ZN15PlayerCharacter5doSecEv': 0x100028730,
    '__ZNK14ItemProperties24SerializeWithCachedSizesEPN6google8protobuf2io17CodedOutputStreamE': 0x100169bf0,
    '__Z13XDL_PlaySoundPKcidd': 0x100100a20,
    '__ZN5flags11drawUniformE': 0x1001f7bfa,
    '__ZN5flags11drawScatterE': 0x1001f7bfb,
    '__ZN5flags8drawEdgeE': 0x1001f7bfc,
    '__ZN5flags9drawTilesE': 0x1001f7bfd,
    '__ZN5flags7drawHUDE': 0x1001f7bfe,
    '__ZN5flags9auraVidIdE': 0x1002180cc,
    '__ZN5flags14serverHostnameE': 0x1002180a8,
    '__ZN10ChatWindowC2EP7ChatLog': 0x1000a5fe0,

    '__ZNK10Properties24SerializeWithCachedSizesEPN6google8protobuf2io17CodedOutputStreamE': 0x10017ba90,
    '__ZN16ServerConnection6doReadEv': 0x1000865e0,
    '_RC4_crypt': 0x10018e0b0,
    '__ZN15MessageHandlers3runE11MessageTypePKci': 0x1000044d0,
    '__ZN12InputMapping3getEv': 0x1000832e0,  # multibox: per-action key bindings
    '__ZN12InputMapping10lookupKeysE11ClientInput': 0x100083370,
    '__ZN10GameClient17handleCreateWorldEPKci': 0x10007c570,
    '__ZN11ClientWorld8spawnObjEv': 0x100015540,
    '__ZN11ClientWorld6getObjERK6ObjKey': 0x1000160e0,
    '__ZN9WorldView22recalculateWorldBoundsEv': 0x1000e0da0,
    '__ZN7TileMap8generateERK9RectangleIiES3_RKNSt3__16vectorIP11WorldObjectNS4_9allocatorIS7_EEEES7_': 0x1000dcc40,
    '__ZTV8GameDest': 0x1001f2960,
    '__ZN8GameDestC1Ev': 0x100160df0,
    '__ZNK8GameDest24SerializeWithCachedSizesEPN6google8protobuf2io17CodedOutputStreamE': 0x100161c00,
    '__ZNK8GameDest8ByteSizeEv': 0x100161d10,
    '__ZNK8GameDest13IsInitializedEv': 0x100161fe0,
    '__ZNK4Join24SerializeWithCachedSizesEPN6google8protobuf2io17CodedOutputStreamE': 0x10010c1e0,
    '__ZNK7Connect24SerializeWithCachedSizesEPN6google8protobuf2io17CodedOutputStreamE': 0x10010dd60,
    '__ZN9HUDStatus4drawEi': 0x1000bc290,
    '__ZN15PlayerCharacter10modifyAmmoEib': 0x100025580,
    '__ZN15PlayerCharacter10applyBoostERK9StatBoost': 0x100026e20,
    '__ZN3HUDC2EiiP11ClientWorldP9WorldView': 0x1000b9700,
    '__ZN11WorldClientC2EiiP16ServerConnectionRK11CreateWorldb': 0x1000f3070,
    '__ZL5stage': 0x1001ff418,
    '__ZL7window_': 0x1001ff710,
    '__ZL8canvasW_': 0x1001ff7c4,
    '__ZL8canvasH_': 0x1002177d0,
    '__ZL20mouseButtonCallback_': 0x1002177f0,
    '__ZL18mouseMoveCallback_': 0x1002177e8,
    '__ZTV5Stage': 0x1001ea140,
    '__ZN18UIElementContainer4drawEi': 0x100078210,
    '__ZN5Stage17handleWindowEventE15XDL_WindowEvent': 0x1000760f0,
    '__ZN18UIElementContainer17handleWindowEventE15XDL_WindowEvent': 0x100078500,
    '__Z12XDL_FillRectiiiij9BlendMode': 0x1000fc5d0,
    '__Z11XDL_FillTriiiiiiij9BlendMode': 0x1000fca50,
    '__Z21XDL_CreateTextTexturejPKcijS0_ij': 0x1000fe920,
    '__Z16XDL_QueryTexturejPiS_': 0x1000ff7c0,
    '__Z15XDL_DrawTexturejiiiiiiiiiiiij9BlendMode': 0x1000fe170,
    '__ZL5flush11FlushReason': 0x1000fbda0,
    '__ZTV9WorldView': 0x1001ee4c0,
    '__ZN9WorldView4drawEi': 0x1000e23a0,
    '__ZN9WorldView14getNameTextureEP11WorldObject': 0x1000e4e60,
    '__ZN9WorldView21getFactionNameTextureEP11WorldObjectP6Player': 0x1000e5430,
    '__ZN5flags12drawHitBoxesE': 0x1002180c3,
    '__ZN5flags9drawBoxesE': 0x1002180c2,
}

def parse(path):
    data = Path(path).read_bytes()
    magic, cpu, subtype, kind, ncmds, _, _, _ = struct.unpack_from('<8I', data)
    assert magic == 0xfeedfacf and cpu == 0x1000007
    assert subtype & 0x00ffffff == 3, "Requires generic Intel x86_64 CPU subtype"
    offset = 32
    commands = []
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', data, offset)
        assert size >= 8 and offset + size <= len(data)
        commands.append((cmd, data[offset:offset + size]))
        offset += size
    return data, kind, commands

def main(game, library):
    data, kind, commands = parse(game)
    assert kind == 2
    assert hashlib.sha256(data).hexdigest() == EXPECTED
    symbols = {}
    for cmd, value in commands:
        if cmd == 0x1b:
            assert value[8:24].hex() == UUID
        elif cmd == 2:
            symoff, count, stroff, _ = struct.unpack_from('<4I', value, 8)
            for i in range(count):
                idx, typ, _, _, addr = struct.unpack_from('<IBBHQ', data, symoff + i * 16)
                if typ & 0xe0 or not addr:
                    continue
                start = stroff + idx
                name = data[start:data.index(b'\0', start)].decode()
                symbols[name] = addr
        elif cmd == 0x19 and value[8:24].rstrip(b'\0') == b'__DATA':
            _, protection = struct.unpack_from('<ii', value, 56)
            assert protection & 2, 'Draw table segment must be writable'
    for name, address in SYMBOLS.items():
        assert symbols.get(name) == address, name
    assert data[0x4cef0:0x4cefd] == bytes.fromhex('55 48 89 e5 48 8d 87 b8 01 00 00 5d c3'), 'Mac ground-loot ItemProperties offset'
    assert struct.unpack_from('<Q', data, 0x1ea168)[0] == 0x100078210
    assert struct.unpack_from('<Q', data, 0x1ea1b0)[0] == 0x1000760f0
    assert struct.unpack_from('<Q', data, 0x1e2f58)[0] == 0x10019049c
    assert struct.unpack_from('<Q', data, 0x1e2c88)[0] == 0x100190118
    assert struct.unpack_from('<Q', data, 0x1e2f80)[0] == 0x1001904ce
    assert struct.unpack_from('<Q', data, 0x1ee1c0)[0] == 0x1000d9fd0
    assert struct.unpack_from('<Q', data, 0x1ee4e8)[0] == 0x1000e23a0
    assert struct.unpack_from('<Q', data, 0x1ee310)[0] == 0x1000dacf0
    assert struct.unpack_from('<Q', data, 0x1ea180)[0] == 0x100076060
    assert struct.unpack_from('<Q', data, 0x1f2998)[0] == 0x100161fe0
    assert struct.unpack_from('<Q', data, 0x1f29c0)[0] == 0x100161c00
    assert struct.unpack_from('<Q', data, 0x1f29b8)[0] == 0x100161d10
    assert struct.unpack_from('<18Q', data, 0x1eba80)[6:9] == (0x1000addd0, 0x10006c840, 0x1000adeb0)
    assert struct.unpack_from('<18Q', data, 0x1eba80)[17] == 0x1000adf80
    assert struct.unpack_from('<17Q', data, 0x1ec290)[5:9] == (0x100078210, 0x1000b3cd0, 0x1000b3d60, 0x1000b3d80)
    assert struct.unpack_from('<17Q', data, 0x1e9a60)[12] == 0x10006df10
    # Instructions in the original Mac HUD/constructor prove scalar field offsets.
    evidence = {
        0x26ca0: '554889e589f02500f00000',  # getNumPos native method prologue
        0x26d01: '8b8718030000',  # native unlocked bag-slot count +0x318
        0xbd1e2: '488b43108b402c',  # native inventory equip destination from Item.desc.slot
        0xbe114: '418d95000f0000',  # bag index to slotPos 0xf00 plus index
        0xbe127: '4963c54869c0565555554889c148c1e93f48c1e82001c88d0c404489ea29ca',  # inventory grid index divided by three columns
        0x15f83: '8b881805000083f94a7f1b',  # native input-budget acceptance threshold
        0x15fba: '488b0f8b460c8b561089c6ff91d0010000',  # native virtual moveItem(source, target) dispatch
        0xf56d6: '84c07415488b7b68be120000004c89f25b415e5de9c106f9ff5b',  # only accepted inventory changes send MT_MODIFY_INV
        0x282e4: '4883bfb001000000',  # native canDoAction rejects any active action, even after emission
        0x2e868: 'ff904801000084c07441',  # doAction repeats virtual eligibility check and takes fatal path on failure
        0x3f680: '554889e54157415641554154534881ecf8010000',  # full Gun::shoot prologue; no relative instructions
        0x3f620: '554889e553504889fb83bbb800000000',  # doUse prologue + cooldown gate at native +0xb8
        0x266b0: '554889e54157415641554154534883ec78',  # moveItem prologue, both integer slots forwarded
        0x15910: '554889e541574156415541545350',  # createObj prologue, all 3 arguments forwarded
        0x3f598: '48c783b40000000000',  # C++ tail-padding reuse: heat +0xb4, cooldown +0xb8 (C struct differs)
        0x3fffc: '8b8088000000418985b8000000',  # Gun::shoot writes descriptor cooldown to weapon +0xb8
        0x3ff0b: '418b9da4000000',  # item animation-speed boost +0xa4
        0x28e3b: '488bbbb0010000',  # native action pointer at +0x1b0 (C struct differs)
        0x255c1: '8b8bd4020000',  # native ammo scalar +0x2d4 in modifyAmmo
        0x26d94: '4c8b8f60030000',  # getItem uses native libc++ map bucket count +0x360
        0x26400: '554889e54157415641554154534883ec68',  # Item test: relocatable addItem prologue
        0x26a50: '554889e54157415641554154534881ec98010000',  # Drop reclaim: complete relocatable prologue
        0x26bb8: '8b904c0100008d4a0189884c010000',  # Native drop allocates old ClientWorld +0x14c ID
        0x45ac0: '554889e58a053e921b00',  # Description cache getter
        0x45ff0: '554889e589f14c8b4f08',  # Native nullable description lookup
        0x26485: 'e866fb01004889c38b4b2c',  # addItem dereferences lookup result without a NULL check
        0x139970: 'a8087418418b7714',  # CharacterProperties HP presence bit and field
        0x13998c: 'a8107418418b7718',  # CharacterProperties max HP presence bit and field
        0x44d0: '554889e5534989d04c8b57084d85d2',  # Common inbound dispatcher relocatable prologue
        0x4cbd0: '554889e54157415641554154534883ec18',  # Item test: relocatable Loot::onUse prologue
        0x4cbf9: '498bb6e8010000',  # Ground item descriptor +0x1e8
        0x4cc13: '498db6b8010000',  # Ground ItemProperties passed to native equip/add
        0x4cd76: '498bb6a8010000',  # Native own ClientSubWorld pointer +0x1a8
        0x265c1: 'e86ae50100',  # tryAdd constructs an actual Item, then setItem
        0x1624a4: '488d0565050900',  # Native StatBoost vtable from its constructor
        0x1624ce: 'c74720ffffffff',  # StatBoost subtype default at native +0x20
        0x14d6e4: '488d05254b0a00',  # native ModifyInv vtable is +0x1001f2210
        0x14d6ee: 'c7471800000000',  # ModifyInv presence bitmap +0x18
        0xf56cd: '488b7b78e89a08f2ff',  # addModifyInv native queue before send
        0x28e89: 'be00010000',  # update timer only for equipped main slot 0x100
        0x28eb7: 'be00020000',  # equipped secondary 0x200 (inventory not updated here)
        0x17ef0a: '8b7318bf04000000',  # WorldProperties floor, field 4 at +0x18
        0x83374: '4863c6488d0c40488b048f8b548f08',  # InputMapping cik[action]: 3 int keys at +action*12
        0x17f023: '488b7340bf0f000000',  # WorldProperties title, field 15 at +0x40
        0x160df0: '554889e5488d05751b0900',  # destination constructor/vtable
        0x161fe9: '8b434489c181e18900000081f989000000',  # required destination fields mask
        0x10c238: 'a8087424488b7320',  # Join destination presence bit and pointer
        0x10de17: 'f6c4027424488b7340',  # Connect Join presence bit and pointer
        0x85e0a: '488b034889dfff5048',  # native send recomputes message ByteSize
        0x865e0: '554889e54157415641554154534881ecc8000000',  # full streaming-receiver entry patch
        0x18e0b0: '554889e58a0f448a4f0185d2',  # native RC4 entry retained by replacement
        0x85d10: '554889e54157415653504889fb4c8d7358',  # complete 17-byte empty-send prologue, before encryption
        0x85db0: '554889e54157415641554154534883ec78',  # complete protobuf-send prologue, before append/encryption
        0x14d6be: 'c747180000000048c747100000000048c7470800000000',  # native PlayerInput initialization
        0xf53f0: '554889e54157415641554154534883ec18',  # complete 17-byte player simulation loop prologue
        0xf5409: '89c1412b4774',  # native lastUpdate at WorldClient +0x74
        0x16e50: '554889e5415741564154534989f6418b8678010000412b460c',  # stock foreign-world throttle helper
        0x15e8c: '498bbde0040000488b07ff5038',  # own sub-world +0x4e0, update virtual slot 0x38
        0x156b4: '488b8f980400008b81780100002b410c',  # received maxT at sub-world +0x178, local interpolation time +0xc
        0x86240: '554889e5415741564154534883ec60',  # complete native I/O frame prologue
        0x8624f: '4989fc',  # native I/O R12=this setup
        0x863d4: 'be020000004c89e7e8c788100041c744242804000000',  # native lost-connection callback argument/receiver
        0x863a5: '668b45be0fbfc8f6c118',  # pollfd revents at RBP-0x42; native ERR/HUP mask
        0x15f01: '39d0750431dbeb58',  # unchanged PlayerInput total returns false
        0xf52fd: '84c07412',  # native setInput sends only accepted changes
        0xf53a7: '84c07412',  # native updateInput sends only accepted changes
        0x863e1: '41c744242804000000',  # native error state after callback
        0x865ed: '4881ecc8000000',  # receive hook's aligned call stack
        0xf4aaf: '4989fc498d9c24b8000000',  # continuation sets native R12=this, RBX=Delta scratch
        0xf4ac9: '498b7c24784889dee86a5cf7ff',  # resume applies already-decoded Delta once
        0x3ef8: 'e8a9bb1800eb0b',  # plain protobuf ParseFromArray returns AL through shared epilogue
        0x3f05: 'e89cbb1800',  # GENC protobuf ParseFromArray before shared epilogue
        0x6a749: '8b4e40',  # Delta presence bitmap +0x40
        0x6a848: 'f6c140',  # state-request-only bit is a legal Delta
        0x163c9: '448b4608',  # WorldUpdate world ID +0x8
        0x163d3: '488bbf98040000',  # server sub-world +0x498
        0x163dc: '4c8b8fc0040000',  # map follows vector: bucket count +0x4c0
        0x6db3: '83fb04',  # GENC requires at least four prefix bytes
        0x6dba: '81fb00001000',  # compressed input bound 1 MiB
        0x6dc2: '458b27410fcc4181fc00001000',  # big-endian expanded size and 1 MiB bound
        0xf4aa0: '554889e5415741564154534883ec20',  # complete, relocatable 15-byte server-delta prologue
        0xf4ac4: 'e8a7f3f0ff',  # native delta decode call
        0xf4b24: '498b7c2468',  # WorldClient server connection +0x68
        0x3e9a: '4183fe25',  # MTC type 0x25 selects decompressDelta
        0x3957: '48c7458800000000',  # CodedInputStream input pointer +0
        0x395f: '48897d90',  # buffer +0x8
        0x396a: '48894d98',  # buffer end +0x10
        0x396e: '8945a0',  # total bytes +0x18
        0x397f: '8945b0',  # current limit +0x28
        0x3989: 'c745b800000004',  # total byte limit +0x30
        0x3990: 'c745bc00000002',  # warning threshold +0x34
        0x39de: '84c00f84ff010000',  # fatal branch on invalid world-ID varint
        0x3a46: '84c00f84ee010000',  # fatal branch on invalid dt varint
        0xfd000: '83f8010f95c00fb6d0',  # SDL left button 1 -> XDL button 0
        0xfcf61: 'bf03000000',  # SDL focus-lost event -> XDL window event 3
        0xad937: '488d35',  # Controls uses native Tabs label names
        0xad93e: 'ba44020000',  # tabs width 580
        0xada43: '4183fe04',  # four original Controls pages
        0xb3968: '448b3e4183ffff',  # empty ClientInput array sentinel -1
        0xb4858: '48c78558ffffff79000000',  # Reset callback uses virtual slot 0x78
        0xdaa01: '41895d38',  # HitNumberGraphic startTime +0x38
        0xdaa6b: '41c7453404000000',  # own critical type 4 at +0x34
        0xdaa7f: '41c7453405000000',  # ally critical type 5 at +0x34
        0xdaab4: '41c7453402000000',  # own normal type 2 at +0x34
        0xdaac3: '41c7453403000000',  # ally normal type 3 at +0x34
        0xdab21: '4d897d50',  # Mac NumberTexture pointer +0x50
        0x8df07: '8903',  # NumberTexture value +0
        0xdacd4: 'b8e8030000',  # number lifetime 1000ms
        0xdacf9: '488b7950',  # number draw uses same texture pointer

        0x7ac8c: '418b86d4000000',  # GameClient idle counter +0xd4
        0xc0555: '49899d10010000',  # MainMenu version pointer +0x110
        0xc0287: '4d89bd00010000',  # MainMenu server chooser +0x100

        0xe0c94: '89b744010000',  # WorldView shake magnitude
        0xe0c9a: '89974c010000',  # WorldView shake duration
        0xe0cd0: '44898760010000',  # WorldView flash color
        0x28749: '8b8300040000',  # Mac secondary spam timer +0x400
        0x2da4c: '4d8dbeb8010000',  # Mac Chest items +0x1b8
        0x2e155: '8b83e8010000',  # Mac Chest pos +0x1e8
        0x169c09: '418b7708',  # ItemProperties type +0x8
        0x169c33: '41837f1800',  # modifier count +0x18
        0x169c3a: '4d8d6710',  # modifier field +0x10
        0xa6063: '48c7477000000000',  # ChatWindow lines +0x70

        0x17bc9d: '8b7354',
        0x17be2c: '488bb388000000',
        0x867bf: '8b459c0fc841894674',  # decoded big-endian uint32_t -> inputLen_
        0x867c8: '8b55d483c2fb8955d449c786c000000000000000',  # guarded boundary
        0x867dc: '493986b8000000',  # next step compares length with allocation
        0x8695a: '31c0eb06',  # existing doRead false-return path
        0x86691: '41c64670008b55d4b00185d20f8fcd000000',  # post-dispatch reconnect boundary
        0x7c5e3: 'e8be341100',  # CreateWorld ParseFromArray call
        0x7c5b6: '488dbd50ffffff',  # parsed CreateWorld lives at RBP-0xb0
        0x7c5dc: '488dbd50ffffff',  # same object passed to ParseFromArray
        0x143ec: '498b7708',  # WorldState server-world pointer +8
        0x14408: '4d636f18',  # client-world repeated field count +0x18
        0x14411: '4d8b7f10',  # client-world repeated elements +0x10
        0x14430: '418b542420',  # client-world owner used as foreign world ID
        0x160e6: '8b0e4883f901',  # object lookup checks server world ID 1 first
        0x16fa7: '8a80a8000000',  # spawn fallback tests WorldObject.props.spawn
        0xe0e53: '41837f5400',  # only terrain contributes native map bounds
        0xe0e5a: '41807f7800',  # drawable terrain
        0xe0e80: '4180bf8500000000',  # bounded terrain contributes inner bounds
        0xe0f4e: 'e8ed45f3ff',  # native spawn resolution before tile generation
        0xe0f68: '4989c0e8d0bcffff',  # resolved pointer is argument R8 to TileMap
        0xdd141: '4883bd18feffff000f84ca060000',  # missing spawn enters fatal branch
        0x7c5e8: '498bb7800000004885f67427488b4678',  # world guard boundary
        0x7c70f: '488dbd50ffffffe8458d0900488d7d80e8c82f1100',  # native protobuf/string cleanup
        0xbc33b: '418b96d0020000',  # maxAmmo.bonus +0x2d0
        0xbc342: '418bb6d4020000',  # ammo +0x2d4
        0xbc34b: '410396cc020000',  # maxAmmo.base +0x2cc
        0xbc35e: '418bb618020000',  # EC +0x218
        0xbc376: '418bb61c020000',  # UC +0x21c
        0x22919: '41c787d802000001000000',  # ammo multiplier +0x2d8
        0xb9802: '49895c2458',  # HUD::hudStatus +0x58
        0x247a7: '498b8678020000',  # Mac PlayerCharacter::charDesc +0x278
        0x2434f: '418b8570020000',  # Item audit: native PlayerCharacter::charId +0x270
        0x270b0: '4883c728',  # max HP tier array +0x28
        0x270bb: '418b9fc4020000',  # max HP base +0x2c4
        0x86d4d: '418b7e54488d75c0ba10000000e8eb8e1000',  # pinned native connect fd/address/length/call
        0x27134: '4883c738',  # max ammo tiers +0x38
        0x2713f: '418b8fcc020000',  # max ammo base +0x2cc
        0x274a1: '4883c748',  # damage tiers +0x48
        0x274ac: '418b8fdc020000',  # damage base +0x2dc
        0x2723a: '4883c760',  # armor tiers +0x60
        0x27245: '418b8fe4020000',  # armor base +0x2e4
        0x27291: '4883c770',  # movement speed tiers +0x70
        0x2729c: '418b8fec020000',  # movement speed base +0x2ec
        0x272eb: '4883ef80',  # jump height tiers +0x80
        0x272f6: '418b8ff4020000',  # jump height base +0x2f4
        0x27558: '4881c790000000',  # crit chance tiers +0x90
        0x27566: '418b8ffc020000',  # crit chance base +0x2fc
        0x274fb: '4881c7a0000000',  # crit multiplier tiers +0xa0
        0x27509: '418b8f04030000',  # crit multiplier base +0x304
        0x8e419: '4c8d4338',  # Mac TextTexture::text +0x38 (8-byte string alignment)
        0x8e48d: '488d7350',  # Mac TextTexture::w +0x50
        0xfe431: 'f20f2a358b131000',  # DrawTexture normalizes X using current canvas on submission
        0xfe466: 'f20f2a3d62931100',  # DrawTexture normalizes Y using current canvas on submission
    }
    for offset, instruction in evidence.items():
        value = bytes.fromhex(instruction)
        assert data[offset:offset+len(value)] == value, hex(offset)
    _, kind, commands = parse(library)
    assert kind == 6, 'Not a Mach-O dylib'
    dependencies = []
    found_minimum = False
    for cmd, value in commands:
        if cmd in (0xc, 0x80000018):
            off = struct.unpack_from('<I', value, 8)[0]
            dependencies.append(value[off:].split(b'\0')[0].decode())
        if cmd == 0x32:
            platform, minimum = struct.unpack_from('<II', value, 8)
            assert platform == 1 and minimum <= 0x000a0e00
            found_minimum = True
        if cmd == 0x24:
            assert struct.unpack_from('<I', value, 8)[0] <= 0x000a0e00
            found_minimum = True
    assert found_minimum
    assert dependencies and all(x in ('/usr/lib/libSystem.B.dylib', '/usr/lib/libz.1.dylib', '/usr/lib/libobjc.A.dylib', '/System/Library/Frameworks/Foundation.framework/Versions/C/Foundation', '/System/Library/Frameworks/CoreFoundation.framework/Versions/A/CoreFoundation') for x in dependencies), dependencies
    print(f'PASS: exact game SHA-256, UUID, {len(SYMBOLS)} native symbol addresses including render flush and WorldView/nameplate methods, writable draw table, original draw slots, GL sampler lazy import slot, Intel Mach-O dylib, macOS 10.14 minimum, system-only dependency; Mac HUD/TextTexture offsets.')

if __name__ == '__main__':
    main(*sys.argv[1:])
