"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../../../components/ui/card";
import { Button } from "../../../../components/ui/button";
import { Input } from "../../../../components/ui/input";
import { ArrowLeft, Save, Play } from "lucide-react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

const formSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters."),
  description: z.string().min(10, "Description must be at least 10 characters."),
});

export default function NewBenchmarkPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
  });

  const onSubmit = (values: z.infer<typeof formSchema>) => {
    console.log("Mock Submit:", values);
    alert("Benchmark draft saved! (Mock)");
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/benchmarks">
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Benchmark Builder</h1>
            <p className="text-muted-foreground mt-1">Design and configure a new evaluation benchmark.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleSubmit(onSubmit)}>
            <Save className="w-4 h-4 mr-2" /> Save Draft
          </Button>
          <Button onClick={handleSubmit(onSubmit)}>
            <Play className="w-4 h-4 mr-2" /> Validate & Publish
          </Button>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>1. Metadata</CardTitle>
            <CardDescription>Basic information about this benchmark.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Benchmark Name</label>
              <Input placeholder="e.g. Advanced Python Coding" {...register("name")} />
              {errors.name && <p className="text-sm text-danger">{errors.name.message}</p>}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <textarea 
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/20 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Describe what this benchmark measures..."
                {...register("description")} 
              />
              {errors.description && <p className="text-sm text-danger">{errors.description.message}</p>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>2. Datasets</CardTitle>
            <CardDescription>Select datasets from the registry to evaluate against.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-32 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground bg-muted/20">
              Dataset selection interface placeholder
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>3. Evaluation Strategy</CardTitle>
            <CardDescription>Configure how the model outputs will be scored.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-32 border-2 border-dashed rounded-lg flex items-center justify-center text-muted-foreground bg-muted/20">
              Judge selection and configuration placeholder
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
