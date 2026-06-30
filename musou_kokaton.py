import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 0.9),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 0.9),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 0.9),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 0.9),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 0.9),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 0.9),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.9)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 1.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = pg.transform.rotozoom(random.choice(__class__.imgs), 0, 0.8)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)




class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class Shield(pg.sprite.Sprite):
    def __init__(self,bird:Bird,life:int):
        super().__init__()
        # surface生成
        width = 20
        height = bird.rect.height * 2
        Surface = pg.Surface((width,height))

        pg.draw.rect(Surface,(0,0,255),(0,0,width,height))
        Surface.set_colorkey((0,0,0))

        vx,vy = bird.dire

        angle = math.degrees(math.atan2(-vy,vx))

        self.image = pg.transform.rotozoom(Surface,angle,1.0)

        self.image.set_colorkey((0,0,0))
        self.rect = self.image.get_rect()

        offset = bird.rect.width
        self.rect.centerx = bird.rect.centerx + vx * offset
        self.rect.centery = bird.rect.centery + vy * offset

        self.life = life

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()
class Life:
    """
    プレイヤーの慚愧を表示・管理するクラス
    """
    def __init__(self, num: int):
        self.num = num
        #40*40の空のSurfaceを作成
        self.heart_surf = pg.Surface((40, 40))
        self.heart_surf.set_colorkey((0, 0, 0))#黒を透過

        points = [(16*math.sin(t/100)**3 +20,
                    -(13*math.cos(t/100)-5*math.cos(2*t/100)-2*math.cos(3*t/100)-math.cos(4*t/100))+20) for t in range(0, 628) ]
        pg.draw.polygon(self.heart_surf, (255, 0, 0), points)

    def update(self, screen: pg.Surface):
        #一番右のライフの中心が右から50、下から50になるようにする
        base_x = WIDTH - 50 - 20
        base_y = HEIGHT - 50 - 20
        for i in range(self.num):
            screen.blit(self.heart_surf, (base_x - i * 40, base_y))


class Gravity(pg.sprite.Sprite): #Spriteクラスを継承
    def __init__(self, life):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        pg.draw.rect(self.image,(0, 0, 0,),(0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(200)
        self.rect = self.image.get_rect()
        self.life = life

    def update(self):
        self.life -= 1

        if self.life == 0: #発動時間が0になったら
            self.kill() #グループから削除


        

    

class Emp(pg.sprite.Sprite):
    """
    電磁パルス(EMP)に関するクラス
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        super().__init__()
        self.life = 2  #0.05秒表示（1フレーム＝0.02秒（50fps）のため、2フレーム表示）

        for emy in emys:
            emy.interval = float("inf")  #爆弾投下できなくなる
            emy.image = pg.transform.laplacian(emy.image)  #ラプラシアンフィルタをかける

        for bomb in bombs:
            bomb.speed /= 2  #動きが遅くなる
            bomb.state = "inactive"  #ぶつかったら起爆せずに消滅する

    def update(self, screen: pg.Surface):
        """
        画面全体に透明度のある黄色の矩形を表示する
        """
        self.life -= 1

        emp_surface = pg.Surface((WIDTH, HEIGHT))
        emp_surface.fill((255, 255, 0))
        emp_surface.set_alpha(35)
        screen.blit(emp_surface, (0, 0))  #渡されたscreenにblitする

        if self.life < 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    life = Life(3)#初期残機数3でLifeインスタンスを作成

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    # 防御壁用グループ
    shields = pg.sprite.Group()
    gravity = pg.sprite.Group()
    emps = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:

                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                
                if event.key == pg.K_s and score.value > 50 and len(shields) == 0:
                    score.value -= 50
                    shields.add(Shield(bird,400))
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key ==pg.K_x and score.value > 200: #重力波はXキーで発動
                gravity.add(Gravity(400))
                score.value -= 200

                # for emy in emys: 
                    
                # emys.empty() #グループを空にする
                # for bomb in bombs:
                     
                # bombs.empty() #グループを空にする

            #eキーが押され、かつスコアが20より大きい場合にEMPを発動
            if event.type == pg.KEYDOWN and event.key == pg.K_e and score.value > 20:
                score.value -= 20
                emps.add(Emp(emys, bombs, screen))  #EMPインスタンスを生成

        screen.blit(bg_img, [0, 0])

        if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, gravity, True, False).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100)) #敵機の位置に爆発エフェクト


        for bomb in pg.sprite.groupcollide(bombs, gravity, True, False).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(bomb, 50))#爆弾の位置に爆発エフェクト
            

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():  # ビームと衝突した敵機リスト
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 10  # 10点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():  # ビームと衝突した爆弾リスト
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 1  # 1点アップ

        for bomb in pg.sprite.spritecollide(bird, bombs, True):  # こうかとんと衝突した爆弾リスト
            life.num -= 1 #残機数を１減少
            bird.change_img(8, screen)  # こうかとん悲しみエフェクト
            if life.num <= 0: #残機数が０になったらゲーム終了
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        
        for bomb in pg.sprite.groupcollide(bombs, shields, True, False).keys():
            exps.add(Explosion(bomb, 50))
            
            # if bomb.state == "inactive":  #EMPによって無効化されている爆弾なら、爆発せずに消滅
            #     continue

            # bird.change_img(8, screen)
            # score.update(screen)
            # pg.display.update()
            # time.sleep(2)
            # return
        
        gravity.draw(screen)
        gravity.update() 
        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)

        shields.update()
        shields.draw(screen)

        emps.update(screen)  #EMPの更新と描画（黄色い矩形を上から被せる）
        score.update(screen)
        score.update(screen)    
        life.update(screen) #updateメゾットでハートをnum個blitする
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
