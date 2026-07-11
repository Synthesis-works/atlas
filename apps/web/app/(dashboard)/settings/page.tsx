"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../components/ui/card";
import { User, Key, Shield, Building2, Bell, Cpu, Check } from "lucide-react";
import { Input } from "../../../components/ui/input";
import { Button } from "../../../components/ui/button";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import * as ToastPrimitive from "@radix-ui/react-toast";
import { cn } from "../../../lib/utils";

const profileSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters."),
  email: z.string().email("Invalid email address."),
});

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("Profile");
  const [toastOpen, setToastOpen] = useState(false);

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<z.infer<typeof profileSchema>>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      fullName: "John Doe",
      email: "john.doe@example.com",
    }
  });

  const onSubmit = async (values: z.infer<typeof profileSchema>) => {
    // Mock API call
    await new Promise(resolve => setTimeout(resolve, 500));
    console.log("Saved profile:", values);
    setToastOpen(true);
  };

  const navItems = [
    { name: "Profile", icon: User },
    { name: "Organization", icon: Building2 },
    { name: "API Keys", icon: Key },
    { name: "Roles & Permissions", icon: Shield },
    { name: "Adapters Config", icon: Cpu },
    { name: "Notifications", icon: Bell },
  ];

  return (
    <ToastPrimitive.Provider swipeDirection="right">
      <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-12">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
          <p className="text-muted-foreground mt-2 text-sm">Manage user preferences, API keys, and platform configuration.</p>
        </div>
        
        <div className="flex flex-col lg:flex-row gap-8">
          <aside className="lg:w-64 space-y-1">
            {navItems.map(item => (
              <button 
                key={item.name}
                onClick={() => setActiveTab(item.name)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
                  activeTab === item.name 
                    ? "bg-accent/80 text-foreground shadow-sm" 
                    : "text-muted-foreground hover:bg-accent/40 hover:text-foreground"
                )}
              >
                <item.icon className="w-4 h-4" /> {item.name}
              </button>
            ))}
          </aside>

          <div className="flex-1 space-y-6">
            {activeTab === "Profile" && (
              <Card className="animate-in fade-in zoom-in-95 duration-200">
                <CardHeader>
                  <CardTitle>Profile Details</CardTitle>
                  <CardDescription>Update your personal information and email address.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center gap-6">
                    <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-primary to-primary/50 flex items-center justify-center text-primary-foreground font-bold text-2xl shadow-lg select-none">
                      JD
                    </div>
                    <Button variant="outline">
                      Change Avatar
                    </Button>
                  </div>

                  <form onSubmit={handleSubmit(onSubmit)} className="grid gap-4 max-w-md">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Full Name</label>
                      <Input {...register("fullName")} />
                      {errors.fullName && <p className="text-sm text-danger">{errors.fullName.message}</p>}
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Email Address</label>
                      <Input disabled {...register("email")} className="bg-muted text-muted-foreground cursor-not-allowed" />
                      <p className="text-xs text-muted-foreground">To change your email, please contact an administrator.</p>
                    </div>
                    <div className="pt-2">
                      <Button type="submit" disabled={isSubmitting}>
                        {isSubmitting ? "Saving..." : "Save Changes"}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            )}

            {activeTab !== "Profile" && (
              <Card className="animate-in fade-in zoom-in-95 duration-200">
                <CardHeader>
                  <CardTitle>{activeTab}</CardTitle>
                  <CardDescription>Configuration options for {activeTab.toLowerCase()}.</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="h-40 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground bg-muted/20">
                    {activeTab} settings placeholder
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>

      <ToastPrimitive.Root 
        open={toastOpen} 
        onOpenChange={setToastOpen}
        className="bg-background border shadow-lg rounded-lg p-4 flex items-center gap-3 data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full"
      >
        <div className="w-8 h-8 rounded-full bg-success/20 flex items-center justify-center text-success">
          <Check className="w-4 h-4" />
        </div>
        <div>
          <ToastPrimitive.Title className="text-sm font-semibold">Profile updated</ToastPrimitive.Title>
          <ToastPrimitive.Description className="text-sm text-muted-foreground">
            Your changes have been saved successfully.
          </ToastPrimitive.Description>
        </div>
        <ToastPrimitive.Close aria-label="Close" className="ml-auto text-muted-foreground hover:text-foreground">
          <span aria-hidden>×</span>
        </ToastPrimitive.Close>
      </ToastPrimitive.Root>
      <ToastPrimitive.Viewport className="fixed bottom-0 right-0 p-6 flex flex-col gap-2 w-[390px] max-w-[100vw] m-0 list-none z-[100] outline-none" />
    </ToastPrimitive.Provider>
  );
}
