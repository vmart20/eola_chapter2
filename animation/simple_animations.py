import numpy as np
import itertools as it

from helpers import *

from mobject import Mobject
from mobject.vectorized_mobject import VMobject
from mobject.tex_mobject import TextMobject
from animation import Animation


class Rotating(Animation):
    CONFIG = {
        "axes"       : [RIGHT, UP],
        "axis"       : None,
        "radians"    : 2*np.pi,
        "run_time"   : 20.0,
        "rate_func"  : None,
        "in_place"   : True,
    }
    def update_mobject(self, alpha):
        axes = [self.axis] if self.axis is not None else self.axes
        families = [
            self.mobject.submobject_family(),
            self.starting_mobject.submobject_family()
        ]
        for mob, start in zip(*families):
            mob.points = np.array(start.points)
        if self.in_place:
            method = self.mobject.rotate_in_place
        else:
            method = self.mobject.rotate           
        method(alpha*self.radians, axes = axes)     


class ShowPartial(Animation):
    CONFIG = {
        "submobject_mode" : None
    }
    def update_mobject(self, alpha):
        self.mobject.become_partial(
            self.starting_mobject, 
            *self.get_bounds(alpha),
            submobject_partial_creation_mode = self.submobject_mode
        )

    def get_bounds(self, alpha):
        raise Exception("Not Implemented")


class ShowCreation(ShowPartial):
    def get_bounds(self, alpha):
        return (0, alpha)

class ShowCreationPerSubmobject(ShowCreation):
    CONFIG = {
        "submobject_mode" : "one_at_a_time",
        "run_time" : 1
    }

class Write(ShowCreation):
    CONFIG = {
        "run_time" : 3,
        "rate_func" : None,
        "submobject_mode" : "lagged_start",
    }
    def __init__(self, mob_or_text, **kwargs):
        if isinstance(mob_or_text, str) or isinstance(mob_or_text, unicode):
            mobject = TextMobject(mob_or_text)
        else:
            mobject = mob_or_text
        ShowCreation.__init__(self, mobject, **kwargs)

class ShowPassingFlash(ShowPartial):
    CONFIG = {
        "time_width" : 0.1
    }
    def get_bounds(self, alpha):
        alpha *= (1+self.time_width)
        alpha -= self.time_width/2
        lower = max(0, alpha - self.time_width/2)
        upper = min(1, alpha + self.time_width/2)
        return (lower, upper)


class Flash(Animation):
    CONFIG = {
        "color" : "white",
        "slow_factor" : 0.01,
        "run_time" : 0.1,
        "rate_func" : None,
    }
    def __init__(self, mobject, **kwargs):
        self.intermediate = Mobject(color = self.color)
        self.intermediate.add_points([
            point + (x, y, 0)
            for point in self.mobject.points
            for x in [-1, 1]
            for y in [-1, 1]
        ])
        Animation.__init__(self, mobject, **kwargs)        

    def update_mobject(self, alpha):
        #Makes alpha go from 0 to slow_factor to 0 instead of 0 to 1
        alpha = self.slow_factor * (1.0 - 4 * (alpha - 0.5)**2)
        self.mobject.interpolate(
            self.starting_mobject, 
            self.intermediate, 
            alpha
        )

class MoveAlongPath(Animation):
    def __init__(self, mobject, vmobject, **kwargs):
        digest_config(self, kwargs, locals())
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        self.mobject.shift(
            self.vmobject.point_from_proportion(alpha) - \
            self.mobject.get_center()
        )

class Homotopy(Animation):
    def __init__(self, homotopy, mobject, **kwargs):
        """
        Homotopy a function from (x, y, z, t) to (x', y', z')
        """
        def function_at_time_t(t):
            return lambda p : homotopy(p[0], p[1], p[2], t)
        self.function_at_time_t = function_at_time_t
        digest_config(self, kwargs)
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        pairs = zip(
            self.mobject.submobject_family(),
            self.starting_mobject.submobject_family()
        )
        for mob, start_mob in pairs:
            mob.become_partial(start_mob, 0, 1)
        self.mobject.apply_function(
            self.function_at_time_t(alpha)
        )


class PhaseFlow(Animation):
    CONFIG = {
        "virtual_time" : 1,
        "rate_func" : None,
    }
    def __init__(self, function, mobject, **kwargs):
        digest_config(self, kwargs, locals())        
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        if hasattr(self, "last_alpha"):
            dt = self.virtual_time*(alpha-self.last_alpha)
            self.mobject.apply_function(
                lambda p : p + dt*self.function(p)
            )
        self.last_alpha = alpha

class MoveAlongPath(Animation):
    def __init__(self, mobject, path, **kwargs):
        digest_config(self, kwargs, locals())
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        n = self.path.get_num_points()-1
        point = self.path.points[int(alpha*n)]
        self.mobject.shift(point-self.mobject.get_center())

class UpdateFromFunc(Animation):
    """
    update_function of the form func(mobject), presumably
    to be used when the state of one mobject is dependent
    on another simultaneously animated mobject
    """
    def __init__(self, mobject, update_function, **kwargs):
        digest_config(self, kwargs, locals())
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        self.update_function(self.mobject)


class MaintainPositionRelativeTo(Animation):
    CONFIG = {
        "tracked_critical_point" : ORIGIN
    }
    def __init__(self, mobject, tracked_mobject, **kwargs):
        digest_config(self, kwargs, locals())
        tcp = self.tracked_critical_point
        self.diff = mobject.get_critical_point(tcp) - \
                    tracked_mobject.get_critical_point(tcp)
        Animation.__init__(self, mobject, **kwargs)

    def update_mobject(self, alpha):
        self.mobject.shift(
            self.tracked_mobject.get_critical_point(self.tracked_critical_point) - \
            self.mobject.get_critical_point(self.tracked_critical_point) + \
            self.diff
        )


### Animation modifiers ###

class ApplyToCenters(Animation):
    def __init__(self, AnimationClass, mobjects, **kwargs):
        full_kwargs = AnimationClass.CONFIG
        full_kwargs.update(kwargs)
        full_kwargs["mobject"] = Mobject(*[
            mob.get_point_mobject()
            for mob in mobjects
        ])
        self.centers_container = AnimationClass(**full_kwargs)
        full_kwargs.pop("mobject")
        Animation.__init__(self, Mobject(*mobjects), **full_kwargs)
        self.name = str(self) + AnimationClass.__name__

    def update_mobject(self, alpha):
        self.centers_container.update_mobject(alpha)
        center_mobs = self.centers_container.mobject.split()
        mobjects = self.mobject.split()        
        for center_mob, mobject in zip(center_mobs, mobjects):
            mobject.shift(
                center_mob.get_center()-mobject.get_center()
            )



class DelayByOrder(Animation):
    """
    Modifier of animation.

    Warning: This will not work on all animation types.
    """
    CONFIG = {
        "max_power" : 5
    }
    def __init__(self, animation, **kwargs):
        digest_locals(self)
        self.num_mobject_points = animation.mobject.get_num_points()        
        kwargs.update(dict([
            (attr, getattr(animation, attr))
            for attr in Animation.CONFIG
        ]))
        Animation.__init__(self, animation.mobject, **kwargs)
        self.name = str(self) + str(self.animation)

    def update_mobject(self, alpha):
        dim = self.mobject.DIM
        alpha_array = np.array([
            [alpha**power]*dim
            for n in range(self.num_mobject_points)
            for prop in [(n+1.0)/self.num_mobject_points]
            for power in [1+prop*(self.max_power-1)]
        ])
        self.animation.update_mobject(alpha_array)


class Succession(Animation):
    def __init__(self, *animations, **kwargs):
        if "run_time" in kwargs:
            run_time = kwargs.pop("run_time")
        else:
            run_time = sum([anim.run_time for anim in animations])
        self.num_anims = len(animations)
        self.anims = animations
        mobject = animations[0].mobject
        Animation.__init__(self, mobject, run_time = run_time, **kwargs)

    def __str__(self):
        return self.__class__.__name__ + \
               "".join(map(str, self.anims))

    def update(self, alpha):
        scaled_alpha = alpha*self.num_anims
        self.mobject = self.anims
        for index in range(len(self.anims)):
            self.anims[index].update(scaled_alpha - index)


